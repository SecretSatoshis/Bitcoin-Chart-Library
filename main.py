"""
Bitcoin Chart Library - Visualization Pipeline

This script reads pre-computed data from Bitcoin-Report-Library's CSV output
and generates interactive HTML charts, static PNG images, and optional Dash dashboards.

Data source:
  Default — GitHub Pages: https://secretsatoshis.github.io/Bitcoin-Report-Library/csv/
  Local   — set REPORT_CSV_DIR=../Bitcoin-Report-Library/csv
"""

import sys
import warnings

import pandas as pd

sys.dont_write_bytecode = True

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
from chart_definitions import csv_path, csv_source_is_remote

# Ignore any FutureWarnings
warnings.simplefilter(action="ignore", category=FutureWarning)

# --- Load Pre-Computed Data from Report Library --- #

master_csv = csv_path("master_metrics_data.csv.gz")

try:
    report_data = pd.read_csv(master_csv, index_col=0, parse_dates=True, low_memory=False)
except Exception as e:
    if csv_source_is_remote():
        print(
            f"Error: Could not fetch {master_csv}\n"
            f"  {e}\n"
            "Ensure the Bitcoin-Report-Library GitHub Pages site is deployed."
        )
    else:
        print(
            f"Error: {master_csv} not found.\n"
            "Run Bitcoin-Report-Library/main.py first to generate data."
        )
    sys.exit(1)

drawdown_data = pd.read_csv(csv_path("drawdown_data.csv"))
cycle_low_data = pd.read_csv(csv_path("cycle_low_data.csv"))
halving_data = pd.read_csv(csv_path("halving_data.csv"))

# --- Chart Creation --- #

create_days_since_chart(drawdown_data, chart_drawdowns)
create_days_since_chart(cycle_low_data, chart_cycle_lows)
create_days_since_chart(halving_data, chart_halvings)
create_monthly_returns(report_data)
create_indexed_monthly_returns(report_data)
create_yearly_returns(report_data)
create_indexed_yearly_returns(report_data)

generated_figures = create_charts(report_data, chart_templates)
figures.extend(generated_figures)

# --- Start the Dash App (uncomment to enable) --- #
# app_with_charts = generate_dash_app()
# app_with_charts.run(debug=True, use_reloader=False, host="0.0.0.0", port=8080)
