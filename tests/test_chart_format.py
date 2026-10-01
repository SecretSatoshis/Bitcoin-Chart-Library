"""Chart data transformations: period returns, cycle paths and daily series."""
import numpy as np
import pandas as pd
import pytest
from chart_data import (_daily, _cycles, _seasonal, build_payload, _positive_price_series,
                        _period_baseline, _report_period, _resolve_filter_start_date)
from chart_templates import get_template


def frame(dates,prices):
    return pd.DataFrame({'price_close':prices},index=pd.to_datetime(dates))


def seasonal(data,period='month',indexed=False):
    return _seasonal(data,{'period':period,'indexed':indexed})[0]


def trace(series,name):return next(s for s in series if s['name']==str(name))


@pytest.mark.parametrize('indexed',[False,True])
def test_monthly_baseline_and_missing_calendar_days(indexed):
    data=frame(['2024-07-31','2024-08-01','2024-08-03','2025-07-31','2025-08-01','2025-08-03'],[100,110,130,200,220,260])
    series=seasonal(data,indexed=indexed);current=trace(series,2025)
    assert current['values'][1] is None
    assert pd.Timestamp(current['x'][2]).day==3
    assert current['values'][0]==pytest.approx(220 if indexed else 10)
    assert current['values'][2]==pytest.approx(260 if indexed else 30)
    assert current['values'][3:] == [None]*28
    assert trace(series,'Average MTD Return')['values'][0]==pytest.approx(220 if indexed else 10)


@pytest.mark.parametrize('period,dates',[('month',['2025-08-01','2025-08-02']),('year',['2025-01-01','2025-01-02'])])
def test_indexed_returns_require_prior_baseline(period,dates):
    with pytest.raises(ValueError,match='prior positive close'):
        seasonal(frame(dates,[100,110]),period,True)


@pytest.mark.parametrize('indexed',[False,True])
def test_yearly_prior_close_missing_days_and_first_move(indexed):
    result=seasonal(frame(['2024-12-31','2025-01-01','2025-01-03'],[100,120,130]),'year',indexed)
    current=trace(result,2025)
    assert current['values'][0]==pytest.approx(120 if indexed else 20)
    assert current['values'][1] is None
    assert current['values'][2]==pytest.approx(130 if indexed else 30)
    assert len(current['values'])==365


@pytest.mark.parametrize('indexed',[False,True])
def test_yearly_skips_partial_history_and_excludes_leap_day(indexed):
    dates=pd.date_range('2023-12-31','2024-12-31').append(pd.date_range('2025-01-01','2025-03-01'))
    data=pd.DataFrame({'price_close':np.arange(len(dates))+100.},index=dates)
    data=data.drop(pd.Timestamp('2024-04-01'))
    result=seasonal(data,'year',indexed)
    assert '2024' not in {s['name'] for s in result}
    current=trace(result,'2025');assert len(current['x'])==365
    assert not any(x.endswith('02-29') for x in current['x'])
    leap=seasonal(frame(['2023-12-31','2024-01-01','2024-03-01'],[90,100,120]),'year',indexed)
    assert len(trace(leap,'2024')['x'])==365
    assert trace(leap,'2024')['values'][59]==pytest.approx(120 if indexed else (120/90-1)*100)


def test_historical_averages_exclude_current_year():
    dates=pd.date_range('2023-12-31','2025-01-02');prices=pd.Series(100.,index=dates)
    prices.loc['2024-01-01':'2024-12-30']=110.;prices.loc['2025-01-01':]=200.
    result=seasonal(prices.to_frame('price_close'),'year')
    assert trace(result,'2025')['values'][0]==100
    assert trace(result,'Average YTD Return')['values'][0]==pytest.approx(10)
    assert trace(result,'Median YTD Return')['values'][0]==pytest.approx(10)


def test_earliest_year_reaches_baseline_before_cutoff():
    result=seasonal(frame(['2013-07-31','2014-08-01','2015-07-31','2015-08-01'],[100,150,200,220]))
    assert trace(result,2014)['values'][0]==50
    assert trace(result,2015)['values'][0]==pytest.approx(10)


def test_period_comes_from_data_not_clock():
    prices=_positive_price_series(pd.Series([100,110],index=pd.to_datetime(['2019-03-30','2019-03-31'])))
    assert _report_period(prices)==(2019,3)
    assert _resolve_filter_start_date('report_month_start',prices.index)==pd.Timestamp('2019-03-01')
    assert _resolve_filter_start_date('report_year_start',prices.index)==pd.Timestamp('2019-01-01')
    assert _period_baseline(prices,2019) is None


def test_cycle_current_low_reconciliation_and_registered_groups():
    master=frame(['2026-02-06','2026-02-07','2026-02-08'],[100,80,120])
    template=get_template('Bitcoin_Cycle_Low');template['y_data']=[{'name':'Current','group':'Current'}]
    data=pd.DataFrame({'Cycle':['Current']*2,'days_since_cycle_low':[0,1],'index_value':[1.,1.5]})
    assert _cycles(data,template,master)[0][0]['values']==[80,120]
    data.loc[0,'index_value']=1.1
    with pytest.raises(ValueError,match='disagrees'):_cycles(data,template,master)
    data.loc[0,'Cycle']='Unknown'
    with pytest.raises(ValueError,match='unregistered'):_cycles(data,template,master)


def test_daily_precision_gaps_optional_and_required_series():
    data=frame(pd.date_range('2026-01-01',periods=4),[10.1234567890123,20,30,40])
    data['benchmark']=[np.nan,15,np.inf,35]
    t=get_template('Bitcoin_Hashrate_Price');t['y_data']=[{'data':'price_close','name':'Bitcoin','axis':'right'}, {'data':'benchmark','name':'Benchmark','axis':'right'}]
    series,_,_=_daily(data,t)
    assert series[0]['values'][0]==10.1234567890123
    assert series[1]['values']==[None,15,None,35]
    with pytest.raises(ValueError,match='Missing required'):_daily(data.drop(columns='benchmark'),t)
    t['y_data'][1]['optional']=True
    with pytest.warns(RuntimeWarning):assert _daily(data.drop(columns='benchmark'),t)[1]==['Benchmark']


def test_dual_axes_units_and_percentage_values_are_explicit():
    t=get_template('Bitcoin_Hash_Ribbons')
    assert t['axes']['left']['unit']=='hashrate' and t['axes']['right']['unit']=='USD'
    t=get_template('Bitcoin_YTD_Return_Comparison_full');t['y_data']=t['y_data'][:1]
    data=frame(pd.date_range('2026-01-01',periods=3),[1,2,3]);data['price_close_ytd_change']=[-12.125,0,215.75]
    p=build_payload(t,{'master_metrics_data.csv.gz':data})
    assert p['series'][0]['values']==[-12.125,0,215.75]
    assert p['axes']['right']['unit']=='percent'

