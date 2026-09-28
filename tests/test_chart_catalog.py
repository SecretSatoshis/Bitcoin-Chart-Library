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
    assert 'plotly' not in document.lower() and 'noindex' not in document
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


def test_catalog_is_offline_capable_and_uses_one_lazy_iframe():
    document=(CHARTS/'index.html').read_text()
    frames=re.findall(r'<iframe\b[^>]*>',document)
    assert len(frames)==1 and not re.search(r'\bsrc\s*=',frames[0])
    inline=json.loads(re.search(r'<script id="catalog-data" type="application/json">(.*?)</script>',document,re.S).group(1))
    assert inline==CATALOG
    assert 'fetch(' not in (ROOT/'web/catalog/assets/catalog.js').read_text()


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
    # The source config is the one maintained by hand; builds copy it into the pack.
    config=json.loads((CHARTS.parent/'web/catalog/vercel.json').read_text())
    headers={r['source']:r['headers'] for r in config['headers']}
    assert '/plotly.min.js' not in headers
    for key in ('/catalog.json','/:chart.html','/'):
        assert 'must-revalidate' in headers[key][0]['value']
    hashed = headers['/assets/(.*\\.[0-9a-f]{16}\\.(?:js|css))'][0]['value']
    assert 'immutable' in hashed
    # Unversioned assets must stay replaceable, so they are never marked immutable.
    unversioned = headers['/assets/(favicon\\.png|logo\\.png|LICENSE|NOTICE|.*-OFL\\.txt)'][0]['value']
    assert 'immutable' not in unversioned
    assert (CHARTS/'assets/LICENSE').is_file() and (CHARTS/'assets/NOTICE').is_file()
