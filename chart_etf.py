"""ETF presentation transforms over verified, published inputs; no new data collection."""
from __future__ import annotations

import datetime as dt
import warnings

import numpy as np
import pandas as pd
from chart_style import BITCOIN_ORANGE, PALETTE, series_color

FUNDS = {
    'IBIT': 'BlackRock', 'FBTC': 'Fidelity', 'GBTC': 'Grayscale', 'BTC': 'Grayscale Mini',
    'ARKB': 'ARK / 21Shares', 'BITB': 'Bitwise', 'HODL': 'VanEck', 'BRRR': 'CoinShares',
    'EZBC': 'Franklin', 'BTCO': 'Invesco / Galaxy', 'BTCW': 'WisdomTree', 'MSBT': 'Morgan Stanley',
}
FUND_COLORS = dict(zip(FUNDS, PALETTE))
GREEN, RED = '#78C99A', '#E87878'
# Issuers publish after the US close, so ETF tables trail the release by a trading day,
# more over weekends and market holidays. Beyond this threshold, warn and render a stale banner
# on ETF pages instead of aborting all 54 charts.
MAX_LAG_BUSINESS_DAYS = 4

# Notable unscheduled NYSE closures (National Days of Mourning, etc.).
_NYSE_SPECIAL_CLOSURES = (
    dt.date(2025, 1, 9),  # National Day of Mourning for President Jimmy Carter
)


def _easter_sunday(year: int) -> dt.date:
    """Anonymous Gregorian algorithm for Easter Sunday."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month, day = divmod(h + ell - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def _observed(date: dt.date) -> dt.date:
    """NYSE observed date for fixed-date holidays (Sat -> Fri, Sun -> Mon)."""
    if date.weekday() == 5:
        return date - dt.timedelta(days=1)
    if date.weekday() == 6:
        return date + dt.timedelta(days=1)
    return date


def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> dt.date:
    first = dt.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + dt.timedelta(days=offset + (nth - 1) * 7)


def _last_weekday(year: int, month: int, weekday: int) -> dt.date:
    if month == 12:
        last = dt.date(year, 12, 31)
    else:
        last = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - dt.timedelta(days=offset)


def nyse_holidays(start_year: int, end_year: int) -> list[str]:
    """Return ISO dates of NYSE market holidays across [start_year, end_year] inclusive."""
    holidays: set[dt.date] = set()
    for year in range(start_year, end_year + 1):
        # New Year's Day (if Jan 1 is Saturday, NYSE observes Friday Dec 31 of prior year
        # only when it isn't excluded; standard observed rule covers Sat/Sun).
        holidays.add(_observed(dt.date(year, 1, 1)))
        holidays.add(_nth_weekday(year, 1, 0, 3))    # MLK Day (3rd Mon Jan)
        holidays.add(_nth_weekday(year, 2, 0, 3))    # Presidents' Day (3rd Mon Feb)
        holidays.add(_easter_sunday(year) - dt.timedelta(days=2))  # Good Friday
        holidays.add(_last_weekday(year, 5, 0))      # Memorial Day (last Mon May)
        if year >= 2022:
            holidays.add(_observed(dt.date(year, 6, 19)))  # Juneteenth
        holidays.add(_observed(dt.date(year, 7, 4)))       # Independence Day
        holidays.add(_nth_weekday(year, 9, 0, 1))    # Labor Day (1st Mon Sep)
        holidays.add(_nth_weekday(year, 11, 3, 4))   # Thanksgiving (4th Thu Nov)
        holidays.add(_observed(dt.date(year, 12, 25)))     # Christmas Day
    for special in _NYSE_SPECIAL_CLOSURES:
        if start_year - 1 <= special.year <= end_year + 1:
            holidays.add(special)
    return sorted(day.isoformat() for day in holidays)


def nyse_trading_days_between(start_date: dt.date, end_date: dt.date) -> int:
    """Count NYSE trading days elapsed from start_date to end_date."""
    cal = np.busdaycalendar(holidays=nyse_holidays(min(start_date.year, end_date.year) - 1,
                                                   max(start_date.year, end_date.year) + 1))
    return int(np.busday_count(start_date, end_date, busdaycal=cal))


def _ordered_funds(daily: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Return (ticker, display_name, color) for all funds present in daily, known funds first."""
    present = set(daily['fund'].dropna().astype(str))
    ordered: list[tuple[str, str, str]] = []
    for fund, name in FUNDS.items():
        if fund in present:
            ordered.append((fund, name, FUND_COLORS[fund]))
    for fund in sorted(present - set(FUNDS)):
        ordered.append((fund, fund, series_color(f'etf_{fund}')))
    return ordered


def _reference_price(daily: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """Prefer IBIT's 4pm reference price, falling back to cross-fund median when IBIT is absent."""
    ibit = daily.loc[daily.fund.eq('IBIT')].set_index('date')['price_usd']
    ibit = pd.to_numeric(ibit, errors='coerce').reindex(index)
    median_price = pd.to_numeric(daily['price_usd'], errors='coerce').groupby(daily['date']).median().reindex(index)
    return ibit.combine_first(median_price)


def _validate_aggregates(daily: pd.DataFrame, totals: pd.DataFrame) -> None:
    """Check that per-fund daily observations reconcile with published daily totals."""
    holdings = daily.groupby('date').btc_held.sum(min_count=1).reindex(totals.index)
    if not np.allclose(holdings, totals.total_btc, rtol=1e-8, equal_nan=False):
        raise ValueError('ETF holdings disagree with the published aggregate')
    checks = (
        ('flow_btc', 'total_flow_btc', 1e-6, 1e-4, 'BTC flows'),
        ('flow_usd', 'total_flow_usd', 1e-6, 1.0, 'USD flows'),
        ('net_assets_usd', 'total_net_assets_usd', 1e-6, 10.0, 'net assets'),
    )
    for daily_col, total_col, rtol, atol, label in checks:
        if daily_col not in daily.columns or total_col not in totals.columns:
            continue
        summed = pd.to_numeric(daily[daily_col], errors='coerce').groupby(daily['date']).sum(min_count=1).reindex(totals.index)
        published = pd.to_numeric(totals[total_col], errors='coerce')
        # Report Library intentionally leaves aggregate flows blank (NaN) on
        # incomplete trailing days (<80% AUM coverage); validate every day where
        # a published aggregate exists.
        published_mask = published.notna()
        if not np.allclose(
            summed[published_mask].to_numpy(dtype=float),
            published[published_mask].to_numpy(dtype=float),
            rtol=rtol,
            atol=atol,
            equal_nan=False,
        ):
            raise ValueError(f'ETF {label} disagree with the published aggregate')


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


def _unavailable_etf_payload(template, cutoff, reason):
    """Graceful fallback payload when upstream ETF CSVs are omitted from a release."""
    from chart_data import _series

    warnings.warn(reason, RuntimeWarning, stacklevel=3)
    date_str = str(cutoff.date())
    placeholder = _series('etf_unavailable', 'ETF Data Unavailable', [date_str], [None], axis='right')
    extra = {
        'dataDate': date_str,
        'rangeEndDate': date_str,
        'readingPoint': date_str,
        'note': template['note'],
        'stale': True,
        'etfUnavailable': True,
        'staleBanner': f'US spot Bitcoin ETF data is temporarily unavailable in this release ({date_str}).',
    }
    return [placeholder], f'{date_str}/{date_str}', extra


def etf_series(template, inputs):
    """Series, coverage and payload fields for one ETF chart view.

    Reads the release's ETF tables up to the master data's last date, checks that the
    fund rows add up to the published totals, and builds the view the template names.
    Missing or stale ETF tables degrade gracefully with a warning and an on-chart banner
    instead of failing the entire 54-chart build.
    """
    from chart_data import _series

    cutoff = inputs['master_metrics_data.csv.gz'].index[-1]
    if 'etf_daily.csv' not in inputs or 'etf_totals_daily.csv' not in inputs:
        return _unavailable_etf_payload(
            template, cutoff,
            f'ETF input tables are missing for release {cutoff.date()}; rendering degraded ETF chart {template["filename"]}',
        )

    daily = inputs['etf_daily.csv'].copy()
    daily['date'] = pd.to_datetime(daily['date'])
    totals = inputs['etf_totals_daily.csv'].copy()
    totals['date'] = pd.to_datetime(totals['date'])
    daily = daily[daily.date.le(cutoff)]
    totals = totals[totals.date.le(cutoff)].set_index('date').sort_index()
    if totals.empty:
        return _unavailable_etf_payload(
            template, cutoff,
            f'ETF totals table is empty through {cutoff.date()}; rendering degraded ETF chart {template["filename"]}',
        )
    if totals.index.has_duplicates or daily.duplicated(['fund', 'date']).any():
        raise ValueError('ETF data requires unique fund/day observations and daily totals')
    _validate_aggregates(daily, totals)

    lag = nyse_trading_days_between(totals.index[-1].date(), cutoff.date())
    stale_banner = None
    if lag > MAX_LAG_BUSINESS_DAYS:
        stale_banner = (
            f'ETF data is delayed — last updated {totals.index[-1].date()} '
            f'({lag} NYSE trading days before release {cutoff.date()}).'
        )
        warnings.warn(
            f'ETF data ends {totals.index[-1].date()}, {lag} NYSE trading days before the '
            f'release ({cutoff.date()}); rendering stale banner on {template["filename"]}',
            RuntimeWarning,
            stacklevel=2,
        )

    index = totals.index
    funds = _ordered_funds(daily)
    series = []
    unit, view = template['unit'], template['view']
    interval = template.get('_flow_interval', template.get('default_flow_interval', 'daily'))
    suffix = 'btc' if unit == 'BTC' else 'usd'
    extra = {'dataDate': str(index[-1].date()), 'rangeEndDate': str(index[-1].date()),
             'readingPoint': str(index[-1].date()), 'note': template['note']}
    if stale_banner:
        extra['stale'] = True
        extra['staleBanner'] = stale_banner

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
                price = _reference_price(daily, index)
                if price.isna().any():
                    raise ValueError('BTC flows require a Bitcoin reference price for every period end')
                add('price_close_etf', 'Bitcoin Price · 4pm Reference', price, color=BITCOIN_ORANGE)
                extra['note'] += ' Bitcoin price uses the last available 4pm reference price in each period.'
        render = 'stackedBar' if view == 'flows' else 'stackedArea'
        for fund, name, color in funds:
            if fund in pivot:
                label = f'{name} ({fund})' if name != fund else fund
                add(f'etf_{fund}', label, pivot[fund], color=color,
                    axis=flow_axis if view == 'flows' else 'right', render=render, stackGroup='funds')
        add('etf_total', 'Total Net Flow' if view == 'flows' else 'Total Holdings' if unit == 'BTC' else 'Total Assets',
            total_values, axis=flow_axis if view == 'flows' else 'right', color=BITCOIN_ORANGE)
        extra['seriesOrder'] = ['etf_total', *[f'etf_{f}' for f, _, _ in funds]]
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
        ytd_daily = totals.total_flow_usd.groupby(totals.index.year).cumsum()
        ytd = ytd_daily.groupby(totals.index.year).ffill().reindex(index)
        add('etf_ytd_flow', 'YTD Cumulative Net Flow', ytd.to_numpy(), dates=index,
            color=BITCOIN_ORANGE, breakOnYear=True, pointMarkers=True)
        extra['flowInterval'] = interval
        extra['axes'] = {key: dict(value) for key, value in template['axes'].items()}
        extra['axes']['left']['label'] = f'{interval.title()} Net Flow (USD)'
        extra['note'] += f' {interval.title()} bars show the period’s net flows; the line shows YTD net flows at each period end. Unfinished periods are to date.'
        if interval == 'weekly':
            extra['note'] += ' Weeks run Monday–Sunday and split at year-end to preserve the January reset.'
    elif view == 'entry':
        # Prefer IBIT's 4pm reference price, falling back to cross-fund median when absent.
        price = _reference_price(daily, index)
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
