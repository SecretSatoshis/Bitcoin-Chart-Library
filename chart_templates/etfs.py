"""US spot Bitcoin ETF charts, built from the Report Library's ETF tables."""

SOURCE = 'Data Source: ETF issuers & SEC'
HISTORY_NOTE = 'Trading-day observations. Historical holdings and flows include reconstructed and interpolated data.'
FLOW_INTERVALS = ['daily', 'weekly', 'monthly', 'quarterly']


def axis(label, unit='USD', *, signed=False):
    result = {'label': label, 'unit': unit, 'mode': 'linear', 'modes': ['linear']}
    if signed:
        result['reference_lines'] = [{'value': 0, 'label': 'Zero net flow'}]
    return result


def chart(order, filename, title, description, view, axes, *, unit='USD', default_range='ALL', note=HISTORY_NOTE, **extra):
    return {
        'filename': filename, 'title': title, 'description': description,
        'family': 'etf', 'category': 'Bitcoin ETFs', 'data_source': SOURCE, 'catalog_order': order,
        'input_files': ['etf_daily.csv', 'etf_totals_daily.csv'],
        'view': view, 'unit': unit, 'axes': axes, 'y_data': [],
        'default_range': default_range, 'ranges': ['1M', '3M', '6M', 'YTD', '1Y', 'ALL'],
        'note': note, **extra,
    }


def price_and_flows(unit):
    """Bitcoin's 4pm reference price in the main panel, fund flows in the subplot."""
    return dict(
        price_panel=True, flow_intervals=FLOW_INTERVALS, default_flow_interval='daily',
        panels=[{'axis': 'right', 'label': 'Bitcoin Price · 4pm Reference', 'control_label': 'Price', 'weight': 60},
                {'axis': 'left', 'label': f'ETF Net Flows in {unit}', 'control_label': 'Flows', 'weight': 40}])


CHARTS = [
    chart(1, 'Bitcoin_ETF_Cumulative_Flows', 'Cumulative Bitcoin ETF Net Flows',
          'Total net capital entering US spot Bitcoin ETFs since January 2024.',
          'cumulative', {'right': axis('Cumulative Net Flow (USD)')}),
    chart(2, 'Bitcoin_ETF_Assets', 'Bitcoin ETF Total Assets',
          'The value of US spot Bitcoin ETF assets, broken down by fund.',
          'holdings', {'right': axis('Net Assets (USD)')},
          note=HISTORY_NOTE + ' Assets use shares × NAV where available, otherwise holdings × the fund reference price. These are issuer-based figures.'),
    chart(3, 'Bitcoin_ETF_Holdings', 'Bitcoin ETF Bitcoin Holdings',
          'Bitcoin held by US spot ETFs, broken down by fund.',
          'holdings', {'right': axis('Bitcoin Held (BTC)', 'BTC')}, unit='BTC'),
    chart(4, 'Bitcoin_ETF_Entry_Price', 'Bitcoin Price & ETF Entry Prices',
          'Bitcoin’s price compared with net-flow and inflow-only entry-price estimates.',
          'entry', {'right': axis('Bitcoin & Entry Prices (USD)'),
                    'left': axis('Net-Flow Mark-to-Market (USD)', signed=True)},
          panels=[{'axis': 'right', 'label': 'Bitcoin Price & Flow-Weighted Entry Prices', 'control_label': 'Price', 'weight': 68},
                  {'axis': 'left', 'label': 'Net-Flow Mark-to-Market · Estimate', 'control_label': 'Estimate', 'weight': 32}],
          note=HISTORY_NOTE + ' Net entry = cumulative net USD flows / cumulative net BTC flows. Inflow-only uses positive per-fund net flows, not gross purchases. Mark-to-market = cumulative net BTC flows × the 4pm Bitcoin reference price − cumulative net USD flows. It excludes inherited holdings and is not SEC accounting cost or investor profit/loss.'),
    chart(5, 'Bitcoin_ETF_Monthly_Flows', 'Bitcoin ETF Flows & YTD Cumulative',
          'Daily, weekly, or monthly net flows alongside the running total for each calendar year.',
          'monthly', {'left': axis('Weekly Net Flow (USD)', signed=True),
                      'right': axis('YTD Cumulative Net Flow (USD)', signed=True)},
          align_zero=True,
          flow_intervals=['daily', 'weekly', 'monthly'], default_flow_interval='weekly',
          note=HISTORY_NOTE + ' The cumulative line resets each January.'),
    chart(6, 'Bitcoin_ETF_Net_Flows_USD', 'Bitcoin ETF Net Flows',
          'Bitcoin’s price above net flows in USD, broken down by fund.',
          'flows', {'right': axis('Bitcoin Price (USD)'),
                    'left': axis('Daily Net Flow (USD)', signed=True)}, default_range='3M',
          **price_and_flows('USD')),
    chart(7, 'Bitcoin_ETF_Net_Flows_BTC', 'Bitcoin ETF Net Flows in BTC',
          'Bitcoin’s price above net flows in BTC, broken down by fund.',
          'flows', {'right': axis('Bitcoin Price (USD)'),
                    'left': axis('Daily Net Flow (BTC)', 'BTC', signed=True)}, unit='BTC', default_range='3M',
          **price_and_flows('BTC')),
    chart(8, 'Bitcoin_ETF_Flows_Since_Peak', 'Bitcoin ETF Net Flows Since the Peak',
          'Cumulative net flows measured from the highest cumulative inflow balance.',
          'since_peak', {'right': axis('Net Flow Since Peak (USD)', signed=True)}),
]
