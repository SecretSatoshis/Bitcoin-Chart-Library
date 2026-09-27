"""Build a complete static pack atomically, or an isolated frozen-release export."""
from __future__ import annotations
import base64
import hashlib
import html
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from chart_data import build_payload
from chart_inputs import load_chart_inputs
from chart_templates import load_templates, validate_templates
from chart_catalog import _head_block, catalog_from_payloads, write_catalog

ROOT = Path(__file__).resolve().parent
WEB = ROOT/'web'


def safe_json(value):
    return json.dumps(value,separators=(',',':'),allow_nan=False).replace('<','\\u003c')


def prepare_assets(output):
    output=Path(output);(output/'assets').mkdir(parents=True,exist_ok=True)
    lock=json.loads((WEB/'vendor-lock.json').read_text())
    for name,digest in lock['files'].items():
        if hashlib.sha256((WEB/'vendor'/name).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Vendor checksum mismatch: {name}')
    result={}
    shutil.copy2(WEB/'catalog/favicon.ico',output/'favicon.ico')
    for name in ('favicon.png','logo.png'):
        shutil.copy2(WEB/'catalog/assets'/name,output/'assets'/name)
    site_css=(WEB/'site.css').read_text()
    css=(WEB/'chart.css').read_text()+'\n'+site_css
    # Data fonts in the shared CSS also work under file:// with browser CORS enabled.
    for name in ('JetBrainsMono-400.ttf','JetBrainsMono-600.ttf','Syne-700.ttf'):
        css=css.replace(f'fonts/{name}','data:font/ttf;base64,'+base64.b64encode((WEB/'fonts'/name).read_bytes()).decode())
    catalog_css=output/'assets/catalog.css'
    if catalog_css.exists():
        catalog_css.write_text('\n'.join(re.findall(r'@font-face\s*\{[^}]+\}',css))+'\n'+catalog_css.read_text()+'\n'+site_css)
    for key,name,data in [('STYLE','chart.css',css.encode()),('RENDERER','renderer.js',(WEB/'renderer.js').read_bytes()),
                          ('RUNTIME','lightweight-charts.js',(WEB/'vendor/lightweight-charts-5.2.1.js').read_bytes())]:
        digest=hashlib.sha256(data).hexdigest()[:16];stem,suffix=name.rsplit('.',1)
        path=f'assets/{stem}.{digest}.{suffix}';(output/path).write_bytes(data);result[key]=path
    for name in ('LICENSE','NOTICE'):
        shutil.copy2(WEB/'vendor'/name,output/'assets'/name)
    for name in ('JetBrainsMono-OFL.txt','Syne-OFL.txt'):
        shutil.copy2(WEB/'fonts'/name,output/'assets'/name)
    result.update(LICENSE='assets/LICENSE',NOTICEFILE='assets/NOTICE')
    return result


def write_chart(payload,output,assets,filename=None):
    output=Path(output);entry=catalog_from_payloads([payload])['charts'][0]
    text=(WEB/'chart.html').read_text()
    # Reuse the catalog's standard site navigation and footer.
    catalog_page=(WEB/'catalog/index.html').read_text()
    nav=re.search(r'<nav class="site-nav".*?</nav>',catalog_page,re.S).group()
    footer=re.search(r'<footer\b.*?</footer>',catalog_page,re.S).group()
    nav=nav.replace('https://charts.secretsatoshis.com/','index.html')
    footer=footer.replace('class="section-divider"','class="section-divider site-footer"').replace('https://charts.secretsatoshis.com/','index.html')
    attribution='<div class="chart-attribution"><a href="https://www.tradingview.com/" target="_blank" rel="noopener">Charts by TradingView</a><details><summary>Attribution &amp; license</summary><p>@@NOTICE@@</p><a href="@@LICENSE@@">Apache 2.0 license</a> · <a href="@@NOTICEFILE@@">Original notice</a></details></div>'
    footer=footer.replace('<div class="footer-bottom">','<div class="footer-bottom">'+attribution)
    text=text.replace('@@NAV@@',nav).replace('@@FOOTER@@',footer)
    for key,value in {**assets,'TITLE':payload['title'],'DATE':payload['reportDate'],
                      'DESCRIPTION':payload['description'],'CATEGORY':payload['category'].upper(),
                      'AXIS':' · '.join(f'{k.upper()}: {a["label"]}' for k,a in payload['axes'].items()),
                      'SOURCE':payload['source'],'NOTE':payload['note'],
                      'NOTICE':(WEB/'vendor/NOTICE').read_text().strip()}.items():
        text=text.replace('@@'+key+'@@',html.escape(value))
    text=text.replace('@@HEAD@@',_head_block(entry,payload['reportDate'],payload['coverage']))
    text=text.replace('@@PAYLOAD@@',safe_json(payload))
    if '@@' in text:raise ValueError('Unresolved page placeholder')
    path=output/(filename or payload['id']+'.html');path.write_text(text)
    return path


def validate_pack(output,payloads):
    expected={p['id'] for p in payloads}
    actual={p.stem for p in Path(output).glob('*.html') if p.name!='index.html'}
    if actual!=expected:raise ValueError('Incomplete generated chart inventory')
    catalog=json.loads((Path(output)/'catalog.json').read_text())
    if {e['filename'] for e in catalog['charts']}!=expected:raise ValueError('Catalog mismatch')
    for p in payloads:
        document=(Path(output)/(p['id']+'.html')).read_text()
        if 'id="chart-data"' not in document or '<h1>' not in document:raise ValueError('Incomplete chart document')
        if 'plotly' in document.lower() or 'noindex' in document:raise ValueError('Legacy/prototype markup in production')
        for path in re.findall(r'(?:src|href)="(assets/[^"?#]+)',document):
            if not (Path(output)/path).is_file():raise ValueError(f'Missing asset {path}')


def _inputs(csv_dir,frozen_report_date=None):
    source=str(csv_dir).rstrip('/')
    return load_chart_inputs(lambda name:source+'/'+name,frozen_report_date=frozen_report_date)


def build_pack(csv_dir,output=ROOT/'Charts',*,templates=None,frozen_report_date=None):
    started=time.perf_counter();output=Path(output).resolve()
    if output.exists() and any(output.iterdir()) and not (output/'catalog.json').is_file():
        raise ValueError('Refusing to replace a non-generated directory')
    definitions=validate_templates(templates if templates is not None else load_templates())
    inputs=_inputs(csv_dir,frozen_report_date)
    payloads=[build_payload(t,inputs) for t in definitions]
    release=inputs['master_metrics_data.csv.gz'].attrs['release_manifest']
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.chart-stage-',dir=output.parent) as directory:
        stage=Path(directory)/'pack';shutil.copytree(WEB/'catalog',stage)
        assets=prepare_assets(stage)
        for p in payloads:
            p['provenance']={'releaseDate':release['report_date'],'inputs':{k:v['sha256'] if isinstance(v,dict) else v for k,v in release['files'].items() if k in inputs}}
            write_chart(p,stage,assets)
        catalog=write_catalog(stage,payloads)
        validate_pack(stage,payloads)
        # Catalog assets are also content-versioned so caches cannot mix releases.
        index=(stage/'index.html').read_text()
        for name in ('catalog.js','catalog.css'):
            path=stage/'assets'/name;digest=hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            versioned=f'assets/{path.stem}.{digest}{path.suffix}';path.rename(stage/versioned)
            index=re.sub(r'assets/'+re.escape(name)+r'(?:\?[^"\s]*)?',versioned,index)
        (stage/'index.html').write_text(index)
        manifest={'schema_version':1,'renderer':'Lightweight Charts 5.2.1','report_date':catalog['latest_data_date'],
                  'charts':{p['id']:{'payload_sha256':hashlib.sha256(safe_json(p).encode()).hexdigest(),
                                    'html_sha256':hashlib.sha256((stage/(p['id']+'.html')).read_bytes()).hexdigest(),
                                    'series_count':len(p['series']),'coverage':p['coverage']} for p in payloads}}
        (stage/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        backup=Path(directory)/'previous'
        if output.exists():os.replace(output,backup)
        try:os.replace(stage,output)
        except BaseException:
            if backup.exists():os.replace(backup,output)
            raise
    metrics={'seconds':round(time.perf_counter()-started,3),'output_bytes':sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),'chart_count':len(payloads),'report_date':catalog['latest_data_date']}
    return metrics


def build_single(csv_dir,filename,output,*,frozen_report_date):
    """Frozen newsletter export: full release integrity with an explicit past cutoff."""
    from chart_templates import get_template
    payload=build_payload(get_template(filename),_inputs(csv_dir,frozen_report_date))
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    assets=prepare_assets(output.parent)
    return write_chart(payload,output.parent,assets,output.name)
