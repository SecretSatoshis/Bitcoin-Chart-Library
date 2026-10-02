"""ETF date cutoffs, period totals and explicitly modeled flow entry prices."""
import hashlib
import json

import pandas as pd
import pytest

from chart_data import build_payload
from chart_inputs import load_chart_inputs
from chart_templates.etfs import CHARTS


def inputs():
    dates = pd.to_datetime(['2024-12-30', '2024-12-31', '2025-01-02', '2025-01-03'])
    daily = pd.DataFrame([
        {'date': date, 'fund': fund, 'btc_held': held, 'flow_btc': flow,
         'flow_usd': flow * 100, 'price_usd': 100., 'net_assets_usd': held * 100}
        for date, a, b, held_a, held_b in zip(dates, [10., 10., -10., 5.], [0., 0., 5., 0.], [10, 20, 10, 15], [1, 1, 6, 6])
        for fund, flow, held in [('IBIT', a, held_a), ('FBTC', b, held_b)]
    ])
    totals = daily.groupby('date').agg(total_btc=('btc_held', 'sum'), total_flow_btc=('flow_btc', 'sum'),
                                     total_flow_usd=('flow_usd', 'sum'), total_net_assets_usd=('net_assets_usd', 'sum'))
    totals['cumulative_flow_btc'] = totals.total_flow_btc.cumsum()
    totals['cumulative_flow_usd'] = totals.total_flow_usd.cumsum()
    totals['flow_weighted_entry_price'] = totals.cumulative_flow_usd / totals.cumulative_flow_btc
    master = pd.DataFrame({'price_close': [100.]}, index=pd.to_datetime(['2025-01-04']))
    return {'master_metrics_data.csv.gz': master, 'etf_daily.csv': daily, 'etf_totals_daily.csv': totals.reset_index()}


def payload(view, data=None):
    template = next(t for t in CHARTS if t['view'] == view)
    return build_payload(template, inputs() if data is None else data)


def values(p, key):
    return next(s['values'] for s in p['series'] if s['id'] == key)


def view(p, interval):
    """The payload is the default flow frequency; flowViews holds the others."""
    return p if interval == p['defaultFlowInterval'] else {**p, **p['flowViews'][interval]}


def test_etf_data_date_is_separate_from_release_and_fund_stacks_keep_source_values():
    p = payload('flows')
    assert p['reportDate'] == '2025-01-04'
    assert p['readingPoint'] == p['dataDate'] == p['rangeEndDate'] == '2025-01-03'
    assert values(p, 'etf_IBIT') == [1000., 1000., -1000., 500.]
    assert values(p, 'etf_total') == [1000., 1000., -500., 500.]
    assert next(s for s in p['series'] if s['id'] == 'etf_IBIT')['render'] == 'stackedBar'


def test_monthly_flows_sum_and_ytd_resets_at_year_boundary():
    p = view(payload('monthly'), 'monthly')
    assert p['x'] == ['2024-12-31', '2025-01-03']
    assert values(p, 'etf_monthly_flow') == [2000., 0.]
    assert values(p, 'etf_ytd_flow') == [2000., 0.]
    assert next(s for s in p['series'] if s['id'] == 'etf_ytd_flow')['breakOnYear']


def test_peak_rebasing_uses_a_fixed_peak_and_includes_the_peak_at_zero():
    p = payload('since_peak')
    assert p['x'] == ['2024-12-31', '2025-01-02', '2025-01-03']
    assert values(p, 'etf_since_peak') == [0., -500., 0.]
    assert '2024-12-31' in p['note']


def test_inflow_only_keeps_inflows_to_one_fund_on_aggregate_outflow_days():
    data = inputs()
    # FBTC creates 5 BTC for $1000 on an aggregate redemption day. Those
    # creations must count even though the combined BTC flow is negative.
    data['etf_daily.csv'].loc[lambda d: d.fund.eq('FBTC') & d.date.eq(pd.Timestamp('2025-01-02')), 'flow_usd'] = 1000.
    p = payload('entry', data)
    assert values(p, 'etf_inflow_entry')[2] == pytest.approx(3000. / 25.)
    assert values(p, 'etf_inflow_entry')[-1] == pytest.approx(3500. / 30.)
    assert values(p, 'etf_flow_mtm') == [0., 0., 0., 0.]
    assert 'not SEC accounting cost' in p['note']


def test_inconsistent_holdings_and_future_rows_are_rejected_or_excluded():
    data = inputs()
    future = data['etf_totals_daily.csv'].iloc[[-1]].assign(date=pd.Timestamp('2025-02-01'))
    data['etf_totals_daily.csv'] = pd.concat([data['etf_totals_daily.csv'], future])
    assert payload('holdings', data)['x'][-1] == '2025-01-03'
    data['etf_totals_daily.csv'].loc[0, 'total_btc'] += 1
    with pytest.raises(ValueError, match='holdings disagree'):
        payload('holdings', data)


def test_etf_inputs_use_the_release_manifest_checksum(tmp_path):
    from test_chart_inputs import _release
    _release(tmp_path)
    name = 'etf_totals_daily.csv'
    path = tmp_path / name
    path.write_text('date,total_btc\n2026-09-08,1\n')
    manifest_path = tmp_path / 'release_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['files'][name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest))
    assert name in load_chart_inputs(lambda n: tmp_path / n, now='2026-09-09', extra_files=[name])
    path.write_text('date,total_btc\n2026-09-08,2\n')
    with pytest.raises(ValueError, match='does not match'):
        load_chart_inputs(lambda n: tmp_path / n, now='2026-09-09', extra_files=[name])


def test_flow_frequency_sums_every_trading_day_and_keeps_fund_units():
    p = payload('flows')
    assert p['flowIntervals'] == ['daily', 'weekly', 'monthly', 'quarterly']
    assert 'daily' not in p['flowViews']  # the payload itself is the default frequency
    weekly = view(p, 'weekly')
    assert weekly['x'] == ['2025-01-03']  # Monday Dec 30 through Sunday Jan 5
    assert values(weekly, 'etf_IBIT') == [1500.]
    assert values(weekly, 'etf_FBTC') == [500.]
    assert values(weekly, 'etf_total') == [2000.]
    for interval in ['daily', 'weekly', 'monthly', 'quarterly']:
        assert sum(values(view(p, interval), 'etf_total')) == 2000.
    btc_template = next(t for t in CHARTS if t['filename'] == 'Bitcoin_ETF_Net_Flows_BTC')
    btc = build_payload(btc_template, inputs())
    assert [panel['axis'] for panel in btc['panels']] == ['right', 'left']
    assert values(btc['flowViews']['weekly'], 'etf_total') == [20.]
    assert values(btc['flowViews']['weekly'], 'price_close_etf') == [100.]
    assert next(s for s in btc['series'] if s['id'] == 'etf_total')['axis'] == 'left'


def test_quarterly_flow_sums_months_and_retains_the_unfinished_quarter():
    data = inputs()
    dates = pd.to_datetime(['2025-01-30', '2025-01-31', '2025-02-03', '2025-04-01'])
    mapping = dict(zip(pd.to_datetime(data['etf_totals_daily.csv'].date), dates))
    for file in ['etf_daily.csv', 'etf_totals_daily.csv']:
        data[file]['date'] = data[file].date.map(mapping)
    data['master_metrics_data.csv.gz'].index = pd.to_datetime(['2025-04-02'])
    quarter = view(payload('flows', data), 'quarterly')
    assert quarter['x'] == ['2025-02-03', '2025-04-01']
    assert values(quarter, 'etf_total') == [1500., 500.]
    assert quarter['readingPoint'] == '2025-04-01'
    assert 'unfinished periods are to date' in quarter['note']


def test_ytd_is_identical_at_the_cutoff_in_every_frequency_and_splits_new_year_weeks():
    p = payload('monthly')
    assert p['defaultFlowInterval'] == 'weekly'
    assert values(view(p, 'daily'), 'etf_ytd_flow') == [1000., 2000., -500., 0.]
    weekly = view(p, 'weekly')
    assert weekly['x'] == ['2024-12-31', '2025-01-03']
    assert values(weekly, 'etf_monthly_flow') == [2000., 0.]
    for interval in ['daily', 'weekly', 'monthly']:
        assert values(view(p, interval), 'etf_ytd_flow')[-1] == 0.


def test_stale_etf_data_is_refused():
    data = inputs()
    # The release is ten days after the last ETF observation: the tables stopped updating.
    data['master_metrics_data.csv.gz'].index = pd.to_datetime(['2025-01-13'])
    with pytest.raises(ValueError, match='stopped updating'):
        payload('cumulative', data)
    # A weekend between the last trading day and the release is normal.
    data['master_metrics_data.csv.gz'].index = pd.to_datetime(['2025-01-06'])
    assert payload('cumulative', data)['dataDate'] == '2025-01-03'


def test_etf_charts_keep_their_catalog_order():
    from chart_catalog import catalog_from_payloads
    shuffled = sorted(CHARTS, key=lambda t: t['title'])
    catalog = catalog_from_payloads([build_payload(t, inputs()) for t in shuffled])
    assert [c['filename'] for c in catalog['charts']] == [t['filename'] for t in CHARTS]
    assert 'order' not in catalog['charts'][0]
