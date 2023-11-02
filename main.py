# Importing Resources
import warnings
import os
import pandas as pd
import numpy as np
import requests
from io import StringIO
from yahoo_fin import stock_info as si
from datetime import datetime, timedelta
import datetime
import json
import math
import scipy.stats
linregress = scipy.stats.linregress

# Importing From Files
import data_format
from chart_format import create_charts, chart_templates, create_days_since_chart, chart_drawdowns, chart_halvings
from dash_app import generate_dash_app, figures
from data_definitions import (
    tickers, market_data_start_date, moving_avg_metrics, fiat_money_data_top10,
    gold_silver_supply, gold_supply_breakdown, stock_tickers, today, yesterday,
    report_date, filter_data_columns, stats_start_date, valuation_data_metrics,
    valuation_metrics, volatility_windows, correlation_data)

# Ignore any FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Fetch the data
data = data_format.get_data(tickers, market_data_start_date)
data = data_format.calculate_custom_on_chain_metrics(data)
data = data_format.calculate_moving_averages(data, moving_avg_metrics)
data = data_format.calculate_btc_price_to_surpass_fiat(data, fiat_money_data_top10)
data = data_format.calculate_metal_market_caps(data, gold_silver_supply)
data = data_format.calculate_gold_market_cap_breakdown(data, gold_supply_breakdown)
data = data_format.calculate_btc_price_to_surpass_metal_categories(data, gold_supply_breakdown)
data = data_format.calculate_btc_price_for_stock_mkt_caps(data, stock_tickers)
data = data_format.calculate_stock_to_flow_metrics(data)

# Forward fill the data for all columns
data.ffill(inplace=True)
today_date = datetime.date.today()
data = data.loc[:today_date]

# Flatten the list of columns from the dictionary
columns_to_keep = [item for sublist in filter_data_columns.values() for item in sublist]

# Filter the dataframe
filter_data = data[columns_to_keep]

# Run Data Analysis On Report Data
report_data = data_format.run_data_analysis(filter_data, stats_start_date)

# Get Bitcoin Difficulty Blockchain Data
difficulty_report = data_format.check_difficulty_change()

# Calcualte Difficulty Period Changes
difficulty_period_changes = data_format.calculate_metrics_change(difficulty_report, report_data)

# Format Bitcoin Difficulty Blockchain Data Output To Pandas
difficulty_report = pd.DataFrame([difficulty_report])

# Calcualte 52 Week High Low Based On Report Timeframe
weekly_high_low = data_format.calculate_52_week_high_low(report_data, report_date)

# Calcualte Valuation Target Data
valuation_data = data_format.create_valuation_data(report_data, valuation_metrics, report_date)

# Calcualte Grwoth Rate Data
cagr_results = data_format.calculate_rolling_cagr_for_all_metrics(data)

report_data = report_data.merge(cagr_results, left_index=True, right_index=True, how='left')

# Calcuate Sharpe Ratio Data
sharpe_data = data[correlation_data]
sharpe_results = data_format.calculate_daily_sharpe_ratios(sharpe_data)

# Calcuate Correlations
correlation_data = data[correlation_data]

# Drop NA Values
correlation_data = correlation_data.dropna()

# Calculate Bitcoin Correlations
correlation_results = data_format.create_btc_correlation_tables(report_date, tickers, correlation_data)

# --- Data Processing --- #
drawdown_data = data_format.compute_drawdowns(report_data)
create_days_since_chart(drawdown_data, chart_drawdowns, 'Bitcoin_ATH_Drawdown')

halving_data = data_format.compute_halving_days(report_data)
create_days_since_chart(halving_data, chart_halvings, 'Bitcoin_Halving_Cycle')

# --- Chart Creation --- #
generated_figures = create_charts(report_data, chart_templates)
figures.extend(generated_figures)

# --- Start the Dash App --- #
app_with_charts = generate_dash_app()
if os.getenv('RUN_SERVER', 'false') == 'true':
    app_with_charts.run_server(debug=True, use_reloader=False, host='0.0.0.0', port=8080)
