"""ETF presentation transforms over verified, published inputs; no new data collection."""
from __future__ import annotations

import numpy as np
import pandas as pd
from chart_style import BITCOIN_ORANGE, PALETTE

FUNDS = {
    'IBIT': 'BlackRock', 'FBTC': 'Fidelity', 'GBTC': 'Grayscale', 'BTC': 'Grayscale Mini',
    'ARKB': 'ARK / 21Shares', 'BITB': 'Bitwise', 'HODL': 'VanEck', 'BRRR': 'CoinShares',
    'EZBC': 'Franklin', 'BTCO': 'Invesco / Galaxy', 'BTCW': 'WisdomTree', 'MSBT': 'Morgan Stanley',
}
FUND_COLORS = dict(zip(FUNDS, PALETTE))
GREEN, RED = '#78C99A', '#E87878'
# Issuers publish after the US close, so ETF tables trail the release by a trading day,
# more over weekends and market holidays. A longer gap means the Report Library has
# stopped updating them, and the charts would present old flows as current.
MAX_LAG_BUSINESS_DAYS = 4


def period_groups(index, interval, *, split_year=False):
    """Trading-day positions by calendar period, dated at the last observation.

    For the YTD comparison, split a New Year week into two partial weeks so no
    December flows are included in a January bar against the new year's line.
    """
    frequencies = {'daily': 'D', 'weekly': 'W-SUN', 'monthly': 'M', 'quarterly': 'Q-DEC'}
    if interval not in frequencies:
        raise ValueError(f'Unknown flow interval: {interval}')
    groups = {}
    for i, period in enumerate(index.to_period(frequencies[interval])):
        key = (index[i].year, period) if split_year else period
        groups.setdefault(key, []).append(i)
    positions = list(groups.values())
    return positions, pd.DatetimeIndex([index[group[-1]] for group in positions])


def etf_series(template, inputs):
    """Series, coverage and payload fields for one ETF chart view.

    Reads the release's ETF tables up to the master data's last date, checks that the
    fund rows add up to the published totals and that the tables are current, then
    builds the view the template names.
    """
    from chart_data import _series

    cutoff = inputs['master_metrics_data.csv.gz'].index[-1]
    daily = inputs['etf_daily.csv'].copy()
    daily['date'] = pd.to_datetime(daily['date'])
    totals = inputs['etf_totals_daily.csv'].copy()
    totals['date'] = pd.to_datetime(totals['date'])
    daily = daily[daily.date.le(cutoff)]
    totals = totals[totals.date.le(cutoff)].set_index('date').sort_index()
    if totals.empty or totals.index.has_duplicates or daily.duplicated(['fund', 'date']).any():
        raise ValueError('ETF data requires unique fund/day observations and daily totals')
    if set(daily.fund) - set(FUNDS):
        raise ValueError('Register the new ETF name and color before rendering it')
    holdings = daily.groupby('date').btc_held.sum(min_count=1).reindex(totals.index)
    if not np.allclose(holdings, totals.total_btc, rtol=1e-8, equal_nan=False):
        raise ValueError('ETF holdings disagree with the published aggregate')
    lag = int(np.busday_count(totals.index[-1].date(), cutoff.date()))
    if lag > MAX_LAG_BUSINESS_DAYS:
        raise ValueError(f'ETF data ends {totals.index[-1].date()}, {lag} business days before the '
                         f'release ({cutoff.date()}); the Report Library has stopped updating it')

    index = totals.index
    series = []
    unit, view = template['unit'], template['view']
    interval = template.get('_flow_interval', template.get('default_flow_interval', 'daily'))
    suffix = 'btc' if unit == 'BTC' else 'usd'
    extra = {'dataDate': str(index[-1].date()), 'rangeEndDate': str(index[-1].date()),
             'readingPoint': str(index[-1].date()), 'note': template['note']}

    def add(key, name, values, *, axis='right', color=None, render='line', dates=None, **options):
        dates = index if dates is None else dates
        result = _series(key, name, dates.strftime('%Y-%m-%d').tolist(), values,
                         axis=axis, role='highlight' if color == BITCOIN_ORANGE else 'normal')
        result.update(render=render, **options)
        if color:
            result['color'] = color
        series.append(result)
        return result

    if view in ('flows', 'holdings'):
        metric = f'flow_{suffix}' if view == 'flows' else 'btc_held' if unit == 'BTC' else 'net_assets_usd'
        pivot = daily.pivot(index='date', columns='fund', values=metric).reindex(index)
        flow_axis = 'left' if template.get('price_panel') else 'right'
        total_col = f'total_flow_{suffix}' if view == 'flows' else 'total_btc' if unit == 'BTC' else 'total_net_assets_usd'
        total_values = totals[total_col]
        if view == 'flows':
            positions, index = period_groups(totals.index, interval)
            pivot = pd.DataFrame([pivot.iloc[group].sum(min_count=1) for group in positions], index=index)
            total_values = [total_values.iloc[group].sum(min_count=1) for group in positions]
            extra['flowInterval'] = interval
            extra['axes'] = {key: dict(value) for key, value in template['axes'].items()}
            extra['axes'][flow_axis]['label'] = f'{interval.title()} Net Flow ({unit})'
            extra['note'] += f' {interval.title()} flows sum the trading-day net flows in each calendar period; unfinished periods are to date.'
            if interval == 'weekly':
                extra['note'] += ' Weeks run Monday–Sunday.'
            if template.get('price_panel'):
                price = daily[daily.fund.eq('IBIT')].set_index('date').price_usd.reindex(index)
                if price.isna().any():
                    raise ValueError('BTC flows require a Bitcoin reference price for every period end')
                add('price_close_etf', 'Bitcoin Price · 4pm Reference', price, color=BITCOIN_ORANGE)
                extra['note'] += ' Bitcoin price uses the last available 4pm reference price in each period.'
        render = 'stackedBar' if view == 'flows' else 'stackedArea'
        for fund, name in FUNDS.items():
            if fund in pivot:
                add(f'etf_{fund}', f'{name} ({fund})', pivot[fund], color=FUND_COLORS[fund],
                    axis=flow_axis if view == 'flows' else 'right', render=render, stackGroup='funds')
        add('etf_total', 'Total Net Flow' if view == 'flows' else 'Total Holdings' if unit == 'BTC' else 'Total Assets',
            total_values, axis=flow_axis if view == 'flows' else 'right', color=BITCOIN_ORANGE)
        extra['seriesOrder'] = ['etf_total', *[f'etf_{f}' for f in FUNDS]]
    elif view == 'cumulative':
        add('etf_cumulative', 'Cumulative Net Flows', totals.cumulative_flow_usd,
            color=BITCOIN_ORANGE, render='area')
    elif view == 'since_peak':
        peak = totals.cumulative_flow_usd.idxmax()
        values = totals.loc[peak:, 'cumulative_flow_usd'] - totals.at[peak, 'cumulative_flow_usd']
        index = values.index
        add('etf_since_peak', 'Net Flows Since Peak', values, dates=index, color=RED, render='area')
        extra['description'] = f'Net flows since the cumulative inflow peak on {peak:%B} {peak.day}, {peak.year}.'
        extra['note'] += f' Fixed baseline: {peak:%Y-%m-%d}, ${totals.at[peak, "cumulative_flow_usd"] / 1e9:.2f} billion. Changing the visible range does not change this baseline.'
    elif view == 'monthly':
        positions, index = period_groups(totals.index, interval, split_year=True)
        period_flows = [totals.total_flow_usd.iloc[group].sum(min_count=1) for group in positions]
        add('etf_monthly_flow', f'{interval.title()} Net Flow', period_flows, dates=index, axis='left',
            color=GREEN, render='bar', positiveColor=GREEN, negativeColor=RED)
        ytd = totals.total_flow_usd.groupby(totals.index.year).cumsum().reindex(index)
        add('etf_ytd_flow', 'YTD Cumulative Net Flow', ytd.to_numpy(), dates=index,
            color=BITCOIN_ORANGE, breakOnYear=True, pointMarkers=True)
        extra['flowInterval'] = interval
        extra['axes'] = {key: dict(value) for key, value in template['axes'].items()}
        extra['axes']['left']['label'] = f'{interval.title()} Net Flow (USD)'
        extra['note'] += f' {interval.title()} bars show the period’s net flows; the line shows YTD net flows at each period end. Unfinished periods are to date.'
        if interval == 'weekly':
            extra['note'] += ' Weeks run Monday–Sunday and split at year-end to preserve the January reset.'
    elif view == 'entry':
        # One consistent 4pm reference for the price comparison and mark-to-market.
        price = daily[daily.fund.eq('IBIT')].set_index('date').price_usd.reindex(index)
        if price.isna().any():
            raise ValueError('ETF entry chart requires a Bitcoin reference price for every trading day')
        net_entry = totals.flow_weighted_entry_price.where(totals.cumulative_flow_btc.gt(0))
        # Take positive NET flows per fund before summing; aggregate positive days
        # would discard inflows to one fund when another fund redeems more.
        inflows = daily[daily.flow_btc.gt(0) & daily.flow_usd.gt(0)]
        buys = inflows.groupby('date')[['flow_btc', 'flow_usd']].sum().reindex(index, fill_value=0).cumsum()
        inflow_entry = buys.flow_usd.div(buys.flow_btc.where(buys.flow_btc.gt(0)))
        estimate = totals.cumulative_flow_btc * price - totals.cumulative_flow_usd
        add('price_close_etf', 'Bitcoin Price · 4pm Reference', price, color=BITCOIN_ORANGE)
        add('etf_net_entry', 'Net Flow-Weighted Entry Price', net_entry, color='#D5D8E2')
        add('etf_inflow_entry', 'Inflow-Only Entry Price · Estimate', inflow_entry, color='#EA90BA')
        add('etf_flow_mtm', 'Net-Flow Mark-to-Market · Estimate', estimate, axis='left', color=PALETTE[0])
    else:
        raise ValueError(f'Unknown ETF view: {view}')

    extra['readingPoint'] = str(index[-1].date())
    return series, f'{index[0].date()}/{index[-1].date()}', extra
