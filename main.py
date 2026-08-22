"""
Bitcoin Chart Library - Visualization Pipeline

This script reads pre-computed data from Bitcoin-Report-Library's CSV output
and generates interactive HTML charts and optional Dash dashboards.

Data source:
  Default — GitHub Pages: https://secretsatoshis.github.io/Bitcoin-Report-Library/csv/
  Local   — set REPORT_CSV_DIR=../Bitcoin-Report-Library/csv
"""

import os
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
from chart_definitions import csv_path, csv_source_is_remote
from chart_catalog import build_chart_catalog

# Dash is only needed for the optional local preview server, so it is imported lazily
# inside the serve branch rather than at module load — CI installs and imports it on
# every run today purely for a code path it never executes.

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
create_days_since_chart(cycle_low_data, chart_cycle_lows, report_data)
create_days_since_chart(halving_data, chart_halvings)
create_monthly_returns(report_data)
create_indexed_monthly_returns(report_data)
create_yearly_returns(report_data)
create_indexed_yearly_returns(report_data)

generated_figures = create_charts(report_data, chart_templates)

catalog = build_chart_catalog(
    report_date=report_data.index.max(),
    chart_templates=chart_templates,
    cycle_templates=[chart_drawdowns, chart_cycle_lows, chart_halvings],
)
print(
    f"Built chart catalog with {catalog['chart_count']} charts "
    f"through {catalog['latest_data_date']}."
)

# --- Optional local preview server --- #
#
# Opt in with an environment variable instead of editing this file:
#
#     SERVE_DASH=1 python main.py
#
# This used to be a commented-out pair of lines, which meant the only way to preview
# locally was to uncomment them — and committing that state hangs CI. `app.run()` never
# returns, so the workflow's "run the script" step never finishes and the separate
# commit step never executes: charts are generated on the runner and then discarded,
# and the job burns until GitHub's 6-hour timeout. That is exactly what caused the
# 11-day outage between 2026-03-21 and 2026-04-02, ended by commit 78ada9b.
#
# Binding is 127.0.0.1, not 0.0.0.0: with debug=True Dash serves the Werkzeug
# interactive debugger, and exposing that to the local network is a needless risk on a
# developer machine.
if os.environ.get("SERVE_DASH") == "1":
    from dash_app import generate_dash_app, figures

    figures.extend(generated_figures)
    app_with_charts = generate_dash_app()
    app_with_charts.run(
        debug=os.environ.get("DASH_DEBUG") == "1",
        use_reloader=False,
        host="127.0.0.1",
        port=8080,
    )
