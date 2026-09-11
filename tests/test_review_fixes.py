"""Release integrity, cycle scaling, missing observations and runtime regressions."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
import pytest

import chart_format as charts
from chart_inputs import INPUT_FILES, load_chart_inputs, validate_report_dates


def _release(tmp_path):
    master = pd.DataFrame({'price_close': [100., 80., 120.]},
                          index=pd.date_range('2026-09-06', periods=3, name='time'))
    master.to_csv(tmp_path / INPUT_FILES[0])
    for name in INPUT_FILES[1:4]:
        pd.DataFrame({'test': [1]}).to_csv(tmp_path / name, index=False)
    summary = pd.DataFrame({'Report Date': ['2026-09-08'], 'Daily Close': [120.]})
    summary.to_csv(tmp_path / INPUT_FILES[-1], index=False)
    manifest = {'version': 1, 'report_date': '2026-09-08',
                'files': {name: hashlib.sha256((tmp_path/name).read_bytes()).hexdigest() for name in INPUT_FILES}}
    (tmp_path/'chart_input_manifest.json').write_text(json.dumps(manifest))
    return master, summary


def test_manifest_loads_matching_release(tmp_path):
    _release(tmp_path)
    frames = load_chart_inputs(lambda name: tmp_path/name, now='2026-09-09')
    assert len(frames) == 5
    assert frames[INPUT_FILES[0]].price_close.iloc[-1] == 120


def test_release_manifest_is_preferred_when_published(tmp_path):
    master, summary = _release(tmp_path)
    manifest = {
        'schema_version': 1,
        'release_id': '2026-09-08',
        'report_date': '2026-09-08',
        'generated_at': '2026-09-09T00:00:00+00:00',
        'files': {
            name: {'sha256': hashlib.sha256((tmp_path / name).read_bytes()).hexdigest(), 'size_bytes': (tmp_path / name).stat().st_size}
            for name in INPUT_FILES
        },
    }
    (tmp_path / 'release_manifest.json').write_text(json.dumps(manifest))
    frames = load_chart_inputs(lambda name: tmp_path / name, now='2026-09-09')
    assert frames[INPUT_FILES[0]].price_close.iloc[-1] == 120


@pytest.mark.parametrize('filename', INPUT_FILES)
def test_manifest_rejects_one_changed_input(tmp_path, filename):
    _release(tmp_path)
    with (tmp_path/filename).open('ab') as handle:
        handle.write(b'\n')
    with pytest.raises(ValueError, match='does not match'):
        load_chart_inputs(lambda name: tmp_path/name, now='2026-09-09')


@pytest.mark.parametrize('date', ['2026-09-07', '2026-09-09', '2026-10-09'])
def test_release_date_must_match_and_be_completed(tmp_path, date):
    master, summary = _release(tmp_path)
    with pytest.raises(ValueError):
        validate_report_dates(master, summary, date, now='2026-09-09')


def test_release_rejects_missing_or_duplicate_day(tmp_path):
    master, summary = _release(tmp_path)
    for broken in [master.drop(master.index[1]), pd.concat([master, master.iloc[-1:]])]:
        with pytest.raises(ValueError, match='calendar'):
            validate_report_dates(broken, summary, '2026-09-08', now='2026-09-09')


def test_cycle_low_moves_with_actual_low(monkeypatch):
    monkeypatch.setattr(charts, 'save_chart_html', lambda *a: None)
    master = pd.DataFrame({'price_close': [100., 80., 120.]}, index=pd.date_range('2026-02-06', periods=3))
    template = {**charts.chart_cycle_lows, 'y_data': [{'name': 'Current', 'group': 'Current'}]}
    cycle = pd.DataFrame({'Cycle': ['Current']*2, 'days_since_cycle_low': [0, 1], 'index_value': [1., 1.5]})
    figure = charts.create_days_since_chart(cycle, template, master)
    np.testing.assert_allclose(figure.data[0].y, [80., 120.])
    cycle.loc[0, 'index_value'] = 1.1
    with pytest.raises(ValueError, match='disagrees'):
        charts.create_days_since_chart(cycle, template, master)


def test_empty_cycle_and_blank_required_metric_fail(monkeypatch):
    monkeypatch.setattr(charts, 'save_chart_html', lambda *a: None)
    with pytest.raises(ValueError, match='required cycle groups'):
        charts.create_days_since_chart(pd.DataFrame(columns=['Era','days_since_halving','index_value']), charts.chart_halvings)
    frame = pd.DataFrame({item['data']: [np.nan, np.nan] for item in charts.chart_hashrate['y_data']}, index=pd.date_range('2026-01-01', periods=2))
    with pytest.raises(ValueError, match='finite observations'):
        charts.create_line_chart(charts.chart_hashrate, frame)


def test_missing_optional_asset_is_visible_without_aborting():
    template = {**charts.chart_price, 'y_data': [
        {'name':'Bitcoin','data':'price_close','yaxis':'y'},
        {'name':'Optional ETF','data':'SPY_close','optional':True,'yaxis':'y'}]}
    frame = pd.DataFrame({'price_close':[100.,110.], 'SPY_close':[np.nan,np.nan]}, index=pd.date_range('2026-01-01',periods=2))
    with pytest.warns(RuntimeWarning, match='Skipping optional'):
        figure = charts.create_line_chart(template, frame)
    assert len(figure.data) == 1
    assert any('Unavailable: Optional ETF' in (item.text or '') for item in figure.layout.annotations)
    assert not any(item.get('optional') for item in charts.chart_price_ma['y_data'])


def test_supply_chart_contracts():
    assert 'Active' not in charts.chart_1_year_supply['y_data'][1]['name']
    assert 'tx_count_sum_24h' not in {item['data'] for item in charts.macro_supply['y_data']}


def test_export_replaces_stale_runtime_and_versions_reference(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path/'Charts').mkdir()
    runtime = tmp_path/'Charts/plotly.min.js'
    runtime.write_text('broken previous version')
    charts.save_chart_html(go.Figure(go.Scatter(x=[1,2], y=[100,110])), 'test')
    assert runtime.read_text() == get_plotlyjs()
    document = (tmp_path/'Charts/test.html').read_text()
    digest = hashlib.sha256(get_plotlyjs().encode()).hexdigest()[:16]
    assert f'src="plotly.min.js?v={digest}"' in document
    assert 'plotly.js v' not in document  # shared bundle, not an accidental inline copy


def test_unregistered_cycle_is_not_silently_omitted(monkeypatch):
    monkeypatch.setattr(charts, 'save_chart_html', lambda *a: None)
    template = {**charts.chart_halvings, 'y_data': [{'name':'Known','group':'Known'}]}
    data = pd.DataFrame({'Era':['Known','New'], 'days_since_halving':[0,0], 'index_value':[1.,1.]})
    with pytest.raises(ValueError, match='unregistered'):
        charts.create_days_since_chart(data, template)
