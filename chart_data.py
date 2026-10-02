"""Renderer-independent transformations. Source values are never filled or rounded."""
import calendar
from chart_style import series_color
import warnings
import numpy as np
import pandas as pd

MIN_RETURN_YEAR = 2014

def _price_series(selected_metrics):
    """Return one sorted, numeric Bitcoin price per normalized calendar day."""
    if "price_close" not in selected_metrics.columns:
        raise KeyError("selected_metrics must contain a 'price_close' column.")

    prices = pd.to_numeric(selected_metrics["price_close"], errors="coerce").copy()
    index = pd.to_datetime(prices.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    prices.index = index.normalize()
    prices = prices.sort_index()
    prices = prices.groupby(level=0).last().dropna()
    if prices.empty:
        raise ValueError("No valid Bitcoin price data is available.")
    return prices

def _positive_price_series(price_series):
    """Return sorted, daily, positive prices; matches the Report Library's period returns."""
    prices = pd.to_numeric(price_series, errors="coerce").sort_index()
    prices = prices.dropna().loc[lambda values: values > 0]
    return prices.groupby(prices.index.normalize()).last()

def _last_positive_before(price_series, boundary):
    """Return the last positive close before a boundary: the baseline a period return
    is measured from, so the period's first day counts, as in the published MTD/YTD figures.
    """
    prior = price_series.loc[price_series.index < pd.Timestamp(boundary)]
    return prior.iloc[-1] if not prior.empty else np.nan

def _period_baseline(price_series, year, month=None):
    """Baseline close for a year's MTD (month given) or YTD (month omitted) series."""
    boundary = pd.Timestamp(year, month, 1) if month else pd.Timestamp(year, 1, 1)
    baseline = _last_positive_before(price_series, boundary)
    if not np.isfinite(baseline) or baseline <= 0:
        return None
    return float(baseline)

def _report_period(price_series):
    """Reporting year and month from the data, never the clock, so every run of a release agrees."""
    as_of = price_series.index.max()
    return as_of.year, as_of.month

def _resolve_filter_start_date(value, index):
    """Resolve a fixed start date or one relative to the release's month or year."""
    if value not in {"report_month_start", "report_year_start"}:
        return pd.to_datetime(value)

    dates = pd.to_datetime(index)
    if len(dates) == 0 or pd.isna(dates.max()):
        raise ValueError("Cannot resolve a report-period filter from an empty date index.")
    as_of = dates.max()
    month = as_of.month if value == "report_month_start" else 1
    return pd.Timestamp(as_of.year, month, 1)

def _reference_year_dates(year):
    """Return all 365 month/day slots for a year, excluding February 29."""
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    return dates[~((dates.month == 2) & (dates.day == 29))]

def _map_to_reference_year(series, reference_year):
    """Map a dated series to the same month/day in a reference year."""
    mapped = series.copy()
    mapped.index = pd.DatetimeIndex(
        [pd.Timestamp(reference_year, date.month, date.day) for date in series.index]
    )
    return mapped

def _is_complete_non_leap_year(series):
    """Return whether a series has every calendar day except February 29."""
    if len(series) != 365:
        return False
    first = series.index[0]
    last = series.index[-1]
    return (first.month, first.day) == (1, 1) and (last.month, last.day) == (12, 31)


def _series(key, name, x, y, axis='right', role='normal'):
    values = pd.to_numeric(pd.Series(y), errors='coerce').to_numpy(dtype=float)
    return {'id': key, 'name': str(name), 'axis': axis, 'role': role,
            'color': series_color(key, role), 'lineWidth': 3 if role == 'highlight' or key == 'price_close' else 1 if role == 'historical' else 2,
            'lineStyle': 'dashed' if role == 'median' else 'solid',
            'opacity': 0.45 if role == 'historical' else 1,
            'x': list(x), 'values': [float(v) if np.isfinite(v) else None for v in values]}


def _daily(frame, template):
    dates = frame.index
    if not isinstance(dates, pd.DatetimeIndex) or dates.empty or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError('Time series must have a sorted, unique date index')
    start = _resolve_filter_start_date(template.get('filter_start_date', dates[0]), dates)
    selected = frame.loc[start:]
    if selected.empty:
        raise ValueError('Chart filter contains no observations')
    x = selected.index.strftime('%Y-%m-%d').tolist()
    series, unavailable = [], []
    for item in template['y_data']:
        metric = item['data']
        values = pd.to_numeric(selected[metric], errors='coerce') if metric in selected else None
        if values is None or not np.isfinite(values).any():
            if not item.get('optional'):
                raise ValueError(f'Missing required observations: {metric}')
            unavailable.append(item['name'])
            warnings.warn(f'Skipping optional metric {metric}', RuntimeWarning, stacklevel=2)
            continue
        role = 'highlight' if metric.startswith('price_close') and item.get('axis','right') == 'right' else 'normal'
        definition = _series(metric, item['name'], x, values, item.get('axis','right'), role)
        definition['lineStyle'] = item.get('line_style', definition['lineStyle'])
        series.append(definition)
    return series, unavailable, f'{x[0]}/{x[-1]}'


def _cycles(frame, template, master):
    xcol, ycol, group = template['x_data'], template.get('value_col','index_value'), template.get('group_col','Era')
    if {xcol,ycol,group} - set(frame.columns):
        raise ValueError('Missing cycle columns')
    expected = {s['group'] for s in template['y_data']}
    if frame.empty or set(frame[group]) != expected:
        raise ValueError('Missing required cycle groups or unregistered groups')
    for name in expected:
        rows = frame.loc[frame[group] == name, [xcol,ycol]].apply(pd.to_numeric, errors='coerce').sort_values(xcol)
        if not np.isfinite(rows).all().all() or not np.array_equal(rows[xcol], np.arange(len(rows))):
            raise ValueError(f'Cycle {name} requires contiguous integer days starting at zero')
    multiplier = 1.
    if template.get('price_scale'):
        current = frame.loc[frame[group] == template['y_data'][-1]['group']].sort_values(xcol)
        latest, terminal = float(master['price_close'].iloc[-1]), float(current[ycol].iloc[-1])
        if not np.isfinite(latest) or latest <= 0 or terminal <= 0:
            raise ValueError('Current cycle price/index must be positive')
        multiplier = latest / terminal
        dates = master.index[-1] - pd.to_timedelta(current[xcol].iloc[-1] - current[xcol], unit='D')
        if not np.allclose(current[ycol].to_numpy()*multiplier, master['price_close'].reindex(pd.DatetimeIndex(dates)).to_numpy(), rtol=1e-9):
            raise ValueError('Current cycle path disagrees with the master prices')
    result = []
    for i, item in enumerate(template['y_data']):
        rows = frame.loc[frame[group] == item['group']].sort_values(xcol)
        result.append(_series(item['group'],item['name'],rows[xcol].astype(int).tolist(),rows[ycol]*multiplier,
                              role='highlight' if i == len(template['y_data'])-1 else 'normal'))
    return result, [], None


def _seasonal(frame, template):
    all_prices = _positive_price_series(_price_series(frame))
    year, month = _report_period(all_prices)
    monthly, indexed = template['period'] == 'month', template['indexed']
    prices = all_prices if monthly else all_prices[~((all_prices.index.month == 2) & (all_prices.index.day == 29))]
    baseline = _period_baseline(all_prices, year, month if monthly else None)
    if indexed and baseline is None:
        raise ValueError('No prior positive close; refusing to leave an older indexed '+('MTD' if monthly else 'YTD')+' chart in place')
    current = prices[prices.index.year == year]
    if indexed and not monthly and (current.index[0].month,current.index[0].day) != (1,1):
        raise ValueError(f'Price data for {year} does not start on January 1')
    aligned = {}
    for yr in prices.index.year.unique():
        if yr < MIN_RETURN_YEAR:
            continue
        selected = prices[(prices.index.year == yr) & (prices.index.month == month)] if monthly else prices[prices.index.year == yr]
        if selected.empty:
            continue
        if not monthly:
            if (selected.index[0].month,selected.index[0].day) != (1,1):
                continue
            if yr != year and not _is_complete_non_leap_year(selected):
                continue
        prior = _period_baseline(all_prices,yr,month if monthly else None)
        if prior is None:
            continue
        values = selected/prior*baseline if indexed else (selected/prior-1)*100
        if monthly:
            values.index = values.index.day
        else:
            values = _map_to_reference_year(values,year)
        aligned[yr] = values
    if not aligned:
        raise ValueError('No complete price series available for period comparison')
    dates = pd.date_range(pd.Timestamp(year,month,1),periods=calendar.monthrange(year,month)[1]) if monthly else _reference_year_dates(year)
    table = pd.DataFrame(aligned,index=range(1,len(dates)+1) if monthly else dates)
    historical = table.drop(columns=[year], errors='ignore')
    x = dates.strftime('%Y-%m-%d').tolist()
    result = [_series(str(yr),str(yr),x,historical[yr],role='historical') for yr in historical]
    if year in table:
        result.append(_series(str(year),str(year),x,table[year],role='highlight'))
    prefix = 'MTD' if monthly else 'YTD'
    result.extend([_series('median',f'Median {prefix} Return',x,historical.median(axis=1),role='median'),
                   _series('mean',f'Average {prefix} Return',x,historical.mean(axis=1),role='mean')])
    return result, [], f'{min(aligned):04d}-01-01/{frame.index[-1].date()}'


def build_payload(template, inputs):
    """Compact, JSON-safe chart contract shared by website and newsletter exports."""
    master = inputs['master_metrics_data.csv.gz']
    family = template['family']
    extra = {}
    if family == 'timeseries':
        series, unavailable, coverage = _daily(master, template)
    elif family == 'cycle':
        series, unavailable, coverage = _cycles(inputs[template['input']],template,master)
    elif family == 'seasonal':
        series, unavailable, coverage = _seasonal(master,template)
    elif family == 'etf':
        from chart_etf import etf_series
        series, coverage, extra = etf_series(template, inputs)
        unavailable = []
    else:
        raise ValueError(f'Unknown chart family: {family}')
    if not series or not any(v is not None for s in series for v in s['values']):
        raise ValueError(f'{template["filename"]}: no finite observations')
    # One x calendar per chart; series carry only aligned values and their extent.
    x = sorted({x for s in series for x in s['x']})
    for s in series:
        s['start'] = x.index(s['x'][0])
        # Ordinary and seasonal series share x; cycle series are contiguous prefixes.
        if x[s['start']:s['start']+len(s['x'])] != s.pop('x'):
            raise ValueError('Series calendar is not contiguous within chart calendar')
    date = str(master.index[-1].date())
    events = sorted([{'date':d, 'name':e['name']} for e in template.get('events',[]) for d in e['dates']
                     if family != 'cycle' and x[0] <= d <= min(x[-1],date)],key=lambda e:e['date'])
    payload = {'schemaVersion':2,'id':template['filename'],'family':family,'title':template['title'],
            'description':template['description'],'category':template['category'], 'featured':template.get('featured',False),
            'source':template['data_source'],'reportDate':date,'coverage':coverage,
            'axisKind':'days' if family == 'cycle' else 'time','axes':template['axes'],
            'defaultRange':template['default_range'],'x':x,'series':series,'events':events,'unavailable':unavailable,
            'readingPoint':len(series[-1]['values'])-1 if family == 'cycle' else date,
            'note':'Historical paths are rescaled comparisons, not forecasts. Readings compare the same elapsed day.' if family=='cycle' and template.get('price_scale') else
                   'Historical years are aligned to the current calendar. Mean and median exclude the current year.' if family=='seasonal' else
                   template.get('note', 'Daily observations.')}
    payload.update(extra)
    if 'ranges' in template:
        payload['ranges'] = list(template['ranges'])
    if template.get('align_zero'):
        payload['alignZero'] = True
    if 'catalog_order' in template:
        payload['catalogOrder'] = template['catalog_order']

    if 'panels' in template:
        payload['panels'] = [dict(panel) for panel in template['panels']]
    if 'default_hidden_series' in template:
        payload['defaultHiddenSeries'] = list(template['default_hidden_series'])
    if family == 'timeseries' and any(s['id'] == 'price_close' and payload['axes'][s['axis']]['unit'] == 'USD' for s in series):
        payload['candleViews'] = _candle_views(payload, inputs)
    if template.get('default_presentation') == 'candles':
        interval = template.get('default_interval', 'daily')
        if interval not in payload.get('candleViews', {}):
            raise ValueError(f'{template["filename"]}: no {interval} candles for its default presentation')
        payload['defaultPresentation'] = 'candles'
        payload['defaultInterval'] = interval
    if family == 'etf' and template.get('flow_intervals') and '_flow_interval' not in template:
        # The payload itself is the default frequency; flowViews holds only the others.
        payload['flowIntervals'] = list(template['flow_intervals'])
        payload['defaultFlowInterval'] = template['default_flow_interval']
        payload['flowViews'] = {}
        for interval in template['flow_intervals']:
            if interval == template['default_flow_interval']:
                continue
            variant = build_payload({**template, '_flow_interval': interval}, inputs)
            payload['flowViews'][interval] = {key: variant[key] for key in
                ('x', 'series', 'readingPoint', 'coverage', 'note', 'dataDate', 'rangeEndDate', 'axes', 'flowInterval')}
    return payload


def _candle_views(payload, inputs):
    """Select prepared observations; all aggregation stays in the Report Library."""
    all_candles = inputs['bitcoin_candles.csv.gz']
    views = {}
    for interval, filename in [('daily','master_metrics_data.csv.gz'),('weekly','weekly_metrics_data.csv.gz'),('monthly','monthly_metrics_data.csv.gz')]:
        rows = all_candles.loc[all_candles.interval.eq(interval) & all_candles.period_start.ge(pd.Timestamp(payload['x'][0])) & all_candles.observation_date.le(pd.Timestamp(payload['x'][-1]))]
        if rows.empty:
            continue
        dates = pd.DatetimeIndex(rows.period_start)
        frame = inputs[filename].reindex(dates)
        x = dates.strftime('%Y-%m-%d').tolist()
        candles = [{'time': str(row.period_start.date()), 'open': float(row.Open), 'high': float(row.High),
                    'low': float(row.Low), 'close': float(row.Close), 'periodEnd': str(row.period_end.date()),
                    'observationDate': str(row.observation_date.date()), 'complete': bool(row.complete)} for row in rows.itertuples()]
        series = [{**s, 'start':0, 'values':[float(v) if np.isfinite(v) else None for v in pd.to_numeric(frame[s['id']],errors='coerce')]} for s in payload['series']]
        events = []
        for event in payload['events']:
            candle = next((c for c in candles if c['time'] <= event['date'] <= c['observationDate']),None)
            if candle:
                events.append({**event,'originalDate':event['date'],'date':candle['time'],'name':event['name']+' · '+event['date']})
        views[interval] = {'x':x,'events':events,'readingPoint':x[-1],'interval':interval}
        if interval == 'daily':
            # Reuse embedded daily line values; compact OHLC avoids duplicating dates
            # and metric history in every standalone chart.
            views[interval].update(offset=payload['x'].index(x[0]),
                                   ohlc=[[c[k] for k in ('open','high','low','close')] for c in candles])
        else:
            views[interval].update(series=series,candles=candles)
    return views
