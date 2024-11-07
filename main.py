# Importing Resources
import warnings
import pandas as pd
from datetime import timedelta
import sys

sys.dont_write_bytecode = True

# Importing From Files``
import data_format
from chart_format import (
    create_charts,
    chart_templates,
    chart_drawdowns,
    chart_halvings,
    chart_cycle_lows,
    create_days_since_chart,
    create_monthly_returns,
    create_indexed_monthly_returns,
    create_yearly_returns,
    create_indexed_yearly_returns,
)
from dash_app import generate_dash_app, figures
from data_definitions import (
    tickers,
    market_data_start_date,
    moving_avg_metrics,
    fiat_money_data_top10,
    gold_silver_supply,
    gold_supply_breakdown,
    stock_tickers,
    filter_data_columns,
    stats_start_date,
)

# Ignore any FutureWarnings
warnings.simplefilter(action="ignore", category=FutureWarning)

# Fetch the data
data = data_format.get_data(tickers, market_data_start_date)
data = data_format.calculate_custom_on_chain_metrics(data)
data = data_format.calculate_moving_averages(data, moving_avg_metrics)
data = data_format.calculate_btc_price_to_surpass_fiat(data, fiat_money_data_top10)
data = data_format.calculate_metal_market_caps(data, gold_silver_supply)
data = data_format.calculate_gold_market_cap_breakdown(data, gold_supply_breakdown)
data = data_format.calculate_btc_price_to_surpass_metal_categories(
    data, gold_supply_breakdown
)
data = data_format.calculate_btc_price_for_stock_mkt_caps(data, stock_tickers)
data = data_format.calculate_stock_to_flow_metrics(data)
data = data_format.electric_price_models(data)

# Forward fill the data for all columns
data.ffill(inplace=True)

# Flatten the list of columns from the dictionary
columns_to_keep = [item for sublist in filter_data_columns.values() for item in sublist]

# Filter the dataframe
filter_data = data[columns_to_keep]

# Run Data Analysis On Report Data
report_data = data_format.run_data_analysis(filter_data, stats_start_date)

# Calcualte Grwoth Rate Data
cagr_results = data_format.calculate_rolling_cagr_for_all_metrics(data)

report_data = report_data.merge(
    cagr_results, left_index=True, right_index=True, how="left"
)

# --- Data Processing --- #
drawdown_data = data_format.compute_drawdowns(report_data)
create_days_since_chart(drawdown_data, chart_drawdowns)

cycle_low_data = data_format.compute_cycle_lows(report_data)
create_days_since_chart(cycle_low_data, chart_cycle_lows)

halving_data = data_format.compute_halving_days(report_data)

create_days_since_chart(halving_data, chart_halvings)
create_monthly_returns(report_data)
create_indexed_monthly_returns(report_data)
create_yearly_returns(report_data)
create_indexed_yearly_returns(report_data)

# --- Chart Creation --- #
generated_figures = create_charts(report_data, chart_templates)

# Assuming 'figures' is a list you have previously defined to store all your figures
figures.extend(generated_figures)

# --- Start the Dash App --- #
app_with_charts = generate_dash_app()
app_with_charts.run_server(debug=True, use_reloader=False, host="0.0.0.0", port=8080)
