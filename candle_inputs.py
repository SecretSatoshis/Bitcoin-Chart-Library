"""Validate the Report Library-prepared candle inputs every release carries. No aggregation here."""
import numpy as np
import pandas as pd

CANDLE_FILES = ('bitcoin_candles.csv.gz', 'weekly_metrics_data.csv.gz', 'monthly_metrics_data.csv.gz')


def validate_candle_inputs(frames, report_date):
    master = frames['master_metrics_data.csv.gz']
    candles = frames[CANDLE_FILES[0]]
    cutoff = pd.Timestamp(report_date)
    required = {'interval', 'period_start', 'period_end', 'observation_date', 'complete', 'Open', 'High', 'Low', 'Close'}
    if required - set(candles) or set(candles.interval) != {'daily','weekly','monthly'}:
        raise ValueError('Incomplete candle export')
    for key in ('period_start', 'period_end', 'observation_date'):
        candles[key] = pd.to_datetime(candles[key], errors='raise')
    if not candles.complete.isin([True, False]).all():
        raise ValueError('Invalid candle completion flags')
    values = candles[['Open','High','Low','Close']].to_numpy(dtype=float)
    if (not np.isfinite(values).all() or (values <= 0).any()
            or (candles.High < candles[['Open','Low','Close']].max(axis=1)).any()
            or (candles.Low > candles[['Open','High','Close']].min(axis=1)).any()):
        raise ValueError('Invalid candle OHLC values')
    for interval, filename in [('daily',None),('weekly',CANDLE_FILES[1]),('monthly',CANDLE_FILES[2])]:
        rows = candles.loc[candles.interval.eq(interval)]
        dates = pd.DatetimeIndex(rows.period_start)
        frequency = {'daily':'D','weekly':'W-MON','monthly':'MS'}[interval]
        if (dates.empty or not dates.equals(pd.date_range(dates[0],dates[-1],freq=frequency))
                or rows.observation_date.iloc[-1] != cutoff
                or (rows.observation_date > cutoff).any()
                or (rows.observation_date < rows.period_start).any()
                or (rows.observation_date > rows.period_end).any()
                or not rows.complete.equals(rows.observation_date.eq(rows.period_end))):
            raise ValueError(f'Invalid {interval} candle calendar/cutoff')
        if not np.allclose(rows.Close,master.price_close.reindex(pd.DatetimeIndex(rows.observation_date)),rtol=1e-9,atol=1e-8):
            raise ValueError('Candle closes disagree with release prices')
        if filename:
            snapshot = frames[filename]
            if not snapshot.index.equals(dates) or list(snapshot.columns) != list(master.columns):
                raise ValueError('Period metric snapshot does not match candle calendar/schema')
            expected = master.reindex(pd.DatetimeIndex(rows.observation_date)).copy()
            expected.index = snapshot.index
            pd.testing.assert_frame_equal(snapshot,expected,check_dtype=False,check_freq=False,rtol=1e-9,atol=1e-8)
