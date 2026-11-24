"""The built catalog, chart pages, published URLs and cache rules."""
import json
import re
from pathlib import Path
import pytest
from chart_templates import load_templates, validate_templates
from chart_build import safe_json

ROOT=Path(__file__).resolve().parents[1]
CHARTS=ROOT/'Charts'
CATALOG=json.loads((CHARTS/'catalog.json').read_text())


def test_catalog_matches_templates_and_intentional_retirements():
    entries=CATALOG['charts'];registered={t['filename'] for t in load_templates()}
    assert CATALOG['chart_count']==len(entries)==len(registered)
    assert {e['filename'] for e in entries}==registered=={p.stem for p in CHARTS.glob('*.html') if p.name!='index.html'}
    original=json.loads((ROOT/'tests/fixtures/original-chart-inventory.json').read_text())
    retired=set(json.loads((ROOT/'tests/fixtures/retired-chart-inventory.json').read_text()))
    assert retired<=set(original)
    assert not (retired & registered)
    assert set(original)-retired<=registered


@pytest.mark.parametrize('entry',CATALOG['charts'],ids=lambda e:e['filename'])
def test_every_chart_has_complete_payload_and_local_assets(entry):
    document=(CHARTS/entry['url']).read_text()
    assert entry['category'] in CATALOG['categories'] and entry['tags']
    assert entry['description'] and entry['height']>=520
    assert 'noindex' not in document
    p=json.loads(re.search(r'<script id="chart-data" type="application/json">(.*?)</script>',document,re.S).group(1))
    assert p['id']==entry['filename'] and p['reportDate']==CATALOG['latest_data_date']
    assert p['series'] and p['x']
    for s in p['series']:
        assert s['axis'] in p['axes']
        assert s['start']+len(s['values'])<=len(p['x'])
    for asset in re.findall(r'(?:src|href)="(assets/[^"?#]+)',document):assert (CHARTS/asset).is_file()


def test_site_count_and_metadata_follow_catalog():
    source=(ROOT/'web/catalog/index.html').read_text()
    document=(CHARTS/'index.html').read_text()
    count=CATALOG['chart_count']
    assert 'placeholder="Search Bitcoin charts…"' in source
    assert f'Search {count} Bitcoin charts…' in document
    assert f'{count} interactive Bitcoin charts' in document
    assert 'ss:chart-index' in source and 'ss:head' in source


def test_catalog_uses_one_lazy_iframe_and_shared_woff2_and_candles():
    document=(CHARTS/'index.html').read_text()
    frames=re.findall(r'<iframe\b[^>]*>',document)
    assert len(frames)==1 and not re.search(r'\bsrc\s*=',frames[0])
    inline=json.loads(re.search(r'<script id="catalog-data" type="application/json">(.*?)</script>',document,re.S).group(1))
    assert inline==CATALOG
    assert 'fetch(' not in (ROOT/'web/catalog/assets/catalog.js').read_text()
    # D5.2: shared WOFF2 fonts (no base64 TTFs in CSS) and one shared hashed candles.<hash>.json asset.
    css_files = list((CHARTS / 'assets').glob('*.css'))
    assert css_files
    for css_file in css_files:
        text = css_file.read_text()
        assert 'data:font/ttf;base64,' not in text
        assert '.woff2' in text
    woff2_files = list((CHARTS / 'assets').glob('*.woff2'))
    assert len(woff2_files) == 2
    candle_files = list((CHARTS / 'assets').glob('candles.*.json'))
    assert len(candle_files) == 1
    m0_payload = json.loads(re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', (CHARTS / 'Bitcoin_M0.html').read_text(), re.S).group(1))
    assert 'candleViews' not in m0_payload
    assert m0_payload['candlesUrl'] == f'assets/{candle_files[0].name}'


def test_etf_tags_and_featured_shelf_and_signed_axes():
    etf_entries = [e for e in CATALOG['charts'] if e['category'] == 'Bitcoin ETFs']
    assert len(etf_entries) == 8
    for entry in etf_entries:
        assert 'ETF' in entry['tags'], entry['filename']
    assert any(e['filename'] == 'Bitcoin_ETF_Net_Flows_USD' and e['featured'] for e in etf_entries)
    # Every signed/negative chart axis must disallow Log scale.
    for entry in CATALOG['charts']:
        doc = (CHARTS / entry['url']).read_text()
        p = json.loads(re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', doc, re.S).group(1))
        for axis_id, axis in p['axes'].items():
            vals = [v for s in p['series'] if s['axis'] == axis_id for v in s['values'] if v is not None]
            if vals and min(vals) <= 0:
                assert axis.get('modes') == ['linear'], f'{entry["filename"]} {axis_id} allows log on <=0 values'


def test_json_ld_escapes_closing_script_tag():
    from chart_catalog import _head_block
    entry = {'title': 'Test </script>', 'description': 'Desc <tag>', 'url': 'Test.html', 'tags': ['Bitcoin']}
    block = _head_block(entry, '2026-09-29', '2020-01-01/2026-09-29')
    ld = re.search(r'application/ld\+json">(.*?)</script>', block, re.S).group(1)
    assert '<' not in ld
    assert json.loads(ld)['name'] == 'Test </script>'


def test_safe_embedded_json_cannot_close_script():
    value={'text':'</script><script>alert(1)</script>'}
    assert '</script>' not in safe_json(value)
    assert json.loads(safe_json(value))==value


def test_registry_rejects_duplicates_and_invalid_axes():
    t=load_templates()[0]
    with pytest.raises(ValueError,match='duplicate'):validate_templates([t,t])
    t={**t,'filename':'../escape'}
    with pytest.raises(ValueError,match='filename'):validate_templates([t])


def test_cache_rules_and_vendored_runtime():
    config=json.loads((CHARTS.parent/'vercel.json').read_text())
    assert config['outputDirectory']=='Charts'
    assert 'curl' not in config['installCommand']
    assert 'uv==0.13.4' in config['installCommand']
    headers={r['source']:r['headers'] for r in config['headers']}
    global_headers={h['key']:h['value'] for h in headers['/(.*)']}
    assert global_headers['X-Content-Type-Options']=='nosniff'
    assert 'max-age=' in global_headers['Strict-Transport-Security']
    assert 'frame-ancestors' in global_headers['Content-Security-Policy']
    assert 'Referrer-Policy' in global_headers
    assert 'Permissions-Policy' in global_headers
    for key in ('/catalog.json','/:chart.html','/'):
        assert 'must-revalidate' in headers[key][0]['value']
    hashed = headers['/assets/(.*\\.[0-9a-f]{16}\\.(?:js|css|json|woff2))'][0]['value']
    assert 'immutable' in hashed
    # Unversioned assets must stay replaceable, so they are never marked immutable.
    unversioned = headers['/assets/(favicon\\.png|LICENSE|NOTICE|.*-OFL\\.txt)'][0]['value']
    assert 'immutable' not in unversioned
    assert (CHARTS/'assets/LICENSE').is_file() and (CHARTS/'assets/NOTICE').is_file()
