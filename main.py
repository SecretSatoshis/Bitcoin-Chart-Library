"""
Bitcoin Chart Library - Visualization Pipeline

This script reads pre-computed data from Bitcoin-Report-Library's CSV output
and generates interactive HTML charts and optional Dash dashboards.

Data source:
  Default — GitHub Pages: https://secretsatoshis.github.io/Bitcoin-Report-Library/csv/
  Local   — set REPORT_CSV_DIR=../Bitcoin-Report-Library/csv
"""

# This module is the chart pipeline: its body regenerates and overwrites Charts/ at
# import time. Refuse to be imported so a test collector or IDE indexer cannot fetch the
# published CSVs and rewrite the chart set as a side effect.
if __name__ != "__main__":
    raise RuntimeError(
        "main.py is an executable pipeline, not an importable module — importing it "
        "would fetch the published CSVs and overwrite Charts/. Import chart_format or "
        "chart_definitions instead, or run `python main.py`."
    )

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
from chart_definitions import csv_path
from chart_catalog import build_chart_catalog

# Dash is only needed for the optional local preview server, so it is imported lazily
# inside the serve branch rather than at module load — CI installs and imports it on
# every run today purely for a code path it never executes.

# Ignore any FutureWarnings
warnings.simplefilter(action="ignore", category=FutureWarning)

# --- Load Pre-Computed Data from Report Library --- #

from chart_inputs import load_chart_inputs

# Hash-check every input against one release before any chart files are written.
inputs = load_chart_inputs(csv_path)
report_data = inputs["master_metrics_data.csv.gz"]
drawdown_data = inputs["drawdown_data.csv"]
cycle_low_data = inputs["cycle_low_data.csv"]
halving_data = inputs["halving_data.csv"]
print(f"Verified chart inputs through {report_data.index.max().date()}.")

# --- Chart Creation --- #

create_days_since_chart(drawdown_data, chart_drawdowns)
create_days_since_chart(cycle_low_data, chart_cycle_lows, report_data)
create_days_since_chart(halving_data, chart_halvings)

# The four period-return charts each refuse to render rather than leave a stale chart in
# place. That refusal should cost those charts, not the other ~55: an unguarded raise
# here aborts the run before `create_charts` and nothing regenerates at all.
return_chart_failures = []
for _builder in (
    create_monthly_returns,
    create_indexed_monthly_returns,
    create_yearly_returns,
    create_indexed_yearly_returns,
):
    try:
        _builder(report_data)
    except Exception as e:
        return_chart_failures.append(f"{_builder.__name__}: {e}")
        print(f"Warning: {_builder.__name__} did not render — {e}")

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

# Fail the run *after* the rest of the charts have been written, so a period-return
# problem is visible in CI without costing the charts that did build.
if return_chart_failures:
    print(
        "Error: "
        + str(len(return_chart_failures))
        + " period-return chart(s) failed to render:"
    )
    for _failure in return_chart_failures:
        print(f"  - {_failure}")
    sys.exit(1)

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
