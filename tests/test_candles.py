import numpy as np
import pandas as pd
import pytest
from chart_data import build_payload
from chart_templates import get_template
from candle_inputs import validate_candle_inputs


def candle_fixture(**metrics):
    """A two-day release with candles; extra keyword columns are added to every metric frame."""
    master=pd.DataFrame({'price_close':[100.,102.],'model':[90.,np.nan],**metrics},index=pd.date_range('2024-01-01',periods=2,name='date'))
    rows=[]
    for interval,start,end,observed,o,h,l,c,complete in [
        ('daily','2024-01-01','2024-01-01','2024-01-01',99,101,98,100,True),
        ('daily','2024-01-02','2024-01-02','2024-01-02',100,103,99,102,True),
        ('weekly','2024-01-01','2024-01-07','2024-01-02',99,103,98,102,False),
        ('monthly','2024-01-01','2024-01-31','2024-01-02',99,103,98,102,False)]:
        rows.append(dict(interval=interval,period_start=start,period_end=end,observation_date=observed,Open=o,High=h,Low=l,Close=c,complete=complete))
    snapshot=master.iloc[[-1]].copy();snapshot.index=pd.DatetimeIndex(master.index[:1],name='period_start')
    snapshot.insert(0,'observation_date',master.index[-1:])
    return {'master_metrics_data.csv.gz':master,'bitcoin_candles.csv.gz':pd.DataFrame(rows),
            'weekly_metrics_data.csv.gz':snapshot.copy(),'monthly_metrics_data.csv.gz':snapshot.copy()}


def test_prepared_periods_preserve_nulls_and_original_event_dates():
    inputs=candle_fixture();validate_candle_inputs(inputs,'2024-01-02')
    template=get_template('Bitcoin_Price');template['filter_start_date']='2024-01-01'
    template['y_data']=[{'data':'price_close','name':'Bitcoin Price','axis':'right'},{'data':'model','name':'Model','axis':'right'}]
    template['events']=[{'name':'Example event','dates':['2024-01-02']}]
    payload=build_payload(template,inputs);week=payload['candleViews']['weekly']
    assert week['series'][1]['values']==[None]
    assert week['candles'][0]['close']==102
    assert week['candles'][0]['complete'] is False
    assert week['events'][0]['date']=='2024-01-01'
    assert week['events'][0]['originalDate']=='2024-01-02'
    # Candles belong to the Bitcoin USD price; a candle default without it is a template error.
    template['y_data']=template['y_data'][1:]
    with pytest.raises(ValueError,match='no monthly candles'):build_payload(template,inputs)
    template['default_presentation']='line'
    assert 'candleViews' not in build_payload(template,inputs)


def test_period_snapshot_and_cutoff_disagreements_rejected():
    inputs=candle_fixture();inputs['weekly_metrics_data.csv.gz'].iloc[0,2]=90
    with pytest.raises(AssertionError):validate_candle_inputs(inputs,'2024-01-02')
    with pytest.raises(ValueError):validate_candle_inputs(candle_fixture(),'2024-01-01')
