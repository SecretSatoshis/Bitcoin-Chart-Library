"""Shared series identities and a contrasting palette for the dark chart theme."""
import hashlib

BITCOIN_ORANGE = '#F7931A'
PALETTE = (
    '#6D9EFF', '#5FD4D0', '#B39AEE', '#EA90BA',
    '#78C99A', '#D6C778', '#E87878', '#D5D8E2',
    '#4378CF', '#CF59AA', '#A8CA58', '#319AA8',
    '#8464C9', '#B67983', '#A9E6CD', '#809BB9',
)

# Model multiples share the model's color even when displayed in another panel.
ALIASES = {
    '200_day_multiple': '200_day_ma_price_close',
    'mvrv': 'realized_price',
    'metcalfe_price_multiple': 'metcalfe_value',
    'power_law_price_multiple': 'power_law_price',
    'hayes_network_price_multiple': 'hayes_network_price',
    **{f'nvt_price_multiple_{days}d': f'nvt_price_{days}d' for days in (30, 90, 365)},
}

COLORS = {}

def register(metrics, colors=PALETTE):
    COLORS.update(zip(metrics, colors))

register(['SPY', 'QQQ', 'XLK', 'XLF', 'VXUS', 'GLD', 'XLE', 'AGG',
          'VTI', 'MSTR', 'WGMI', 'DX-Y.NYB', 'XLRE', '^SPGSCI', 'XYZ', 'COIN'])
register(['META', 'AMZN', 'GOOGL', 'MSFT', 'AAPL'])
register(['NVDA', 'AVGO', 'TSM', '005930.KS', 'MU'])
register(['united_states_m0_btc_price', 'china_m0_btc_price', 'eurozone_m0_btc_price',
          'japan_m0_btc_price', 'united_kingdom_m0_btc_price', 'switzerland_m0_btc_price',
          'india_m0_btc_price', 'australia_m0_btc_price', 'russia_m0_btc_price'])
register(['gold_market_cap_btc_price', 'silver_market_cap_btc_price',
          'gold_jewellery_market_cap_btc_price', 'gold_private_investment_market_cap_btc_price',
          'gold_official_country_holdings_market_cap_btc_price', 'gold_other_market_cap_btc_price'],
         [PALETTE[i] for i in (5, 7, 2, 1, 3, 0)])
register(['7_day_ma_price_close', '50_day_ma_price_close', '200_day_ma_price_close',
          '200_week_ma_price_close'], [PALETTE[i] for i in (0, 1, 2, 7)])
register(['realized_price', 'sth_realized_price', 'lth_realized_price',
          'realizedcap_multiple_2', 'realizedcap_multiple_3', 'realizedcap_multiple_5'],
         [PALETTE[i] for i in (0, 1, 3, 4, 2, 6)])
register(['thermocap_price', *[f'thermocap_price_multiple_{n}' for n in (4, 8, 16, 32)]])
register(['nvt_price_30d', 'nvt_price_90d', 'nvt_price_365d'],
         [PALETTE[i] for i in (0, 1, 3)])
register(['electricity_cost_4c', 'hayes_network_price', 'electricity_cost_6c'],
         [PALETTE[i] for i in (1, 0, 2)])
register(['power_law_price', 'power_law_price_band_058', 'power_law_price_band_173',
          'power_law_price_band_300'], ['#D5D8E2', '#78C99A', '#DDA76B', '#E87878'])
register(['liquid_supply', 'illiquid_supply', 'sth_supply', 'lth_supply', 'supply'],
         [PALETTE[i] for i in (0, 2, 1, 3, 7)])
register([f'utxos_under_{age}_old_supply' for age in ('1m', '3m', '6m', '1y', '2y', '3y', '4y', '5y', '10y')],
         [PALETTE[i] for i in (0, 1, 2, 3, 4, 5, 6, 8, 9)])
register([f'addrs_over_{balance}_addr_count' for balance in
          ('1sat', '10sats', '100sats', '1k_sats', '10k_sats', '100k_sats', '1m_sats',
           '10m_sats', '1btc', '10btc', '100btc', '1k_btc', '10k_btc')])
for metric in ('tx_count_sum_24h', 'transfer_volume_sum_24h_usd',
               'daily_active_addresses_sending', 'coinbase_sum_24h_usd', 'hash_rate'):
    register([metric, f'30_day_ma_{metric}', f'365_day_ma_{metric}'])
register(['30_day_ma_subsidy_sum_24h', '365_day_ma_subsidy_sum_24h'])
register(['volatility_30d', 'volatility_180d'])
register(['supply_in_profit_pct', 'supply_in_loss_pct'], ['#78C99A', '#E87878'])
COLORS['60_day_ma_hash_rate'] = PALETTE[3]
for metric in ('market_cap', 'sat_per_dollar', 'supply_pct_1_year_plus', 'fees_sum_24h_usd',
               'difficulty', 'hash_price_ths', 'puell_multiple', 'nupl',
               'reserve_risk_calc', 'sopr_24h', 'metcalfe_value'):
    COLORS[metric] = PALETTE[0]


def metric_identity(key):
    key = ALIASES.get(key, key)
    if key.startswith('price_close'):
        return 'bitcoin'
    if key in COLORS:
        return key
    if '_close' in key:
        return key.split('_close', 1)[0]
    if key.endswith('_mc_btc_price'):
        return key.removesuffix('_mc_btc_price')
    return key


def series_color(key, role='normal'):
    identity = metric_identity(key)
    if identity == 'bitcoin' or role == 'highlight':
        return BITCOIN_ORANGE
    if role == 'mean':
        return '#68C5AF'
    if role == 'median':
        return '#DAD9ED'
    if key.isdigit():
        # Historical years keep their identity across monthly/yearly views;
        # leave the teal and pale neutral tones to the mean and median.
        historical = [PALETTE[i] for i in (0, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15)]
        return historical[(int(key) - 2014) % len(historical)]
    if key.startswith(('Drawdown Cycle ', 'Market Cycle ')):
        return PALETTE[(int(key.rsplit(' ', 1)[1]) - 1) % len(PALETTE)]
    if key.endswith(' Era'):
        return PALETTE[(int(key[0]) - 2) % len(PALETTE)]
    return COLORS.get(identity, PALETTE[int(hashlib.sha256(identity.encode()).hexdigest()[:8], 16) % len(PALETTE)])
