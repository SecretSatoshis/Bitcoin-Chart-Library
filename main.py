# --- Importing Resources --- #
import os
import warnings

# --- Importing From Files --- #
from data_format import gather_data, create_report_data, compute_drawdowns, compute_halving_days, tickers, start_date, end_date
from chart_format import create_charts, chart_templates, create_days_since_chart, chart_drawdowns, chart_halvings
from dash_app import generate_dash_app, figures

# Ignore any FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Data Gathering --- #
chart_data = gather_data(tickers, start_date)
selected_metrics = create_report_data(chart_data)

# --- Data Processing --- #
drawdown_data = compute_drawdowns(selected_metrics)
create_days_since_chart(drawdown_data, chart_drawdowns, 'Bitcoin_ATH_Drawdown')

halving_data = compute_halving_days(selected_metrics)
create_days_since_chart(halving_data, chart_halvings, 'Bitcoin_Halving_Cycle')

# --- Chart Creation --- #
generated_figures = create_charts(selected_metrics, chart_templates)
figures.extend(generated_figures)

# --- Start the Dash App --- #
app_with_charts = generate_dash_app()
if os.getenv('RUN_SERVER', 'false') == 'true':
    app_with_charts.run_server(debug=True, use_reloader=False, host='0.0.0.0', port=8080)