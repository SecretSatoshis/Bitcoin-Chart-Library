import copy
import json
from pathlib import Path
import pandas as pd
import pytest
import chart_build
from chart_templates import get_template,load_templates
from candle_inputs import validate_candle_inputs
from test_candles import candle_fixture


@pytest.fixture
def release(monkeypatch):
    inputs=candle_fixture();validate_candle_inputs(inputs,'2024-01-02')
    inputs['master_metrics_data.csv.gz'].attrs['release_manifest']={'report_date':'2024-01-02','files':{}}
    monkeypatch.setattr(chart_build,'_inputs',lambda *a:inputs)
    t=get_template('Bitcoin_Price');t['y_data']=t['y_data'][:1];t['filter_start_date']='2024-01-01'
    return t


def test_new_template_generates_chart_catalog_and_export_contract(tmp_path,release):
    extra=copy.deepcopy(release);extra.update(filename='Bitcoin_New_Template',title='New chart')
    out=tmp_path/'pack'
    chart_build.build_pack('unused',out,templates=[release,extra])
    catalog=json.loads((out/'catalog.json').read_text())
    assert {e['filename'] for e in catalog['charts']}=={release['filename'],extra['filename']}
    assert 'id="chart-data"' in (out/'Bitcoin_New_Template.html').read_text()
    assert 'SecretSatoshisChart' in next((out/'assets').glob('renderer.*.js')).read_text()


def test_failure_keeps_previous_pack_byte_for_byte(tmp_path,release,monkeypatch):
    out=tmp_path/'pack';chart_build.build_pack('unused',out,templates=[release])
    before={str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
    bad=copy.deepcopy(release);bad['y_data'][0]['data']='missing'
    with pytest.raises(ValueError):chart_build.build_pack('unused',out,templates=[bad])
    monkeypatch.setattr(chart_build,'validate_pack',lambda *a:(_ for _ in ()).throw(ValueError('validation failure')))
    with pytest.raises(ValueError):chart_build.build_pack('unused',out,templates=[release])
    assert before=={str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}


def test_refuses_non_generated_output(tmp_path):
    (tmp_path/'precious.txt').write_text('keep')
    with pytest.raises(ValueError,match='non-generated'):chart_build.build_pack('unused',tmp_path)
    assert (tmp_path/'precious.txt').read_text()=='keep'


def test_template_discovery_needs_no_other_registry(tmp_path,monkeypatch):
    import chart_templates
    t=get_template('Bitcoin_Price');t['filename']='New_Discovered_Chart'
    (tmp_path/'extra.py').write_text('CHARTS = '+repr([t]))
    monkeypatch.setattr(chart_templates,'__path__',[str(tmp_path)])
    try:
        assert [t['filename'] for t in chart_templates.load_templates()]==['New_Discovered_Chart']
    finally:
        import sys
        sys.modules.pop('chart_templates.extra',None)


def test_panel_assignment_requires_one_valid_weighted_panel_per_axis():
    from chart_templates import validate_templates
    template=get_template('Bitcoin_Metcalfe_Model')
    validate_templates([template])
    for panels in ([template['panels'][0]], [template['panels'][0]]*2,
                   [{**p,'weight':0} for p in template['panels']]):
        with pytest.raises(ValueError):
            validate_templates([{**template,'panels':panels}])


def test_panel_payload_preserves_existing_observations():
    from chart_data import build_payload
    template=get_template('Bitcoin_Metcalfe_Model')
    template['filter_start_date']='2024-01-01'
    inputs=candle_fixture(metcalfe_value=[50.,51.],metcalfe_price_multiple=[2.,2.])
    validate_candle_inputs(inputs,'2024-01-02')
    with_panels=build_payload(template,inputs)
    single=copy.deepcopy(template);single.pop('panels')
    without_panels=build_payload(single,inputs)
    assert with_panels.pop('panels')==template['panels']
    assert with_panels==without_panels
