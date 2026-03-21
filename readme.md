# Bitcoin Chart Library

Bitcoin visualization and charting platform powering the Secret Satoshis analytics stack. The system delivers interactive dashboards and publication-ready charts for on-chain metrics, valuation models, and cross-asset analysis.

**This is a pure visualization layer.** All data fetching and metric calculation is handled by [Bitcoin-Report-Library](https://github.com/SecretSatoshis/Bitcoin-Report-Library). This project reads pre-computed CSV files and generates charts — no API calls, no data processing.

## Features

- **On-Chain Analytics**: Hash rate, difficulty, transaction metrics, UTXO age bands, address activity, miner revenue, and supply dynamics
- **Valuation Models**: Stock-to-Flow, Thermocap, NVT, Realized Price, electric price models, and relative valuation metrics
- **Cycle Analysis**: Drawdown tracking from ATH, halving epoch comparisons, market cycle low indexing
- **Cross-Asset Comparisons**: Correlations with equities, ETFs, commodities, forex, and fiat money supply
- **Performance Tracking**: Rolling returns (MTD, YTD, YoY), CAGR calculations, and historical return heatmaps
- **Interactive Dashboards**: Web-based Dash application with all charts accessible through a browser

## Architecture

```
Bitcoin-Chart-Library/
├── main.py              # Pipeline orchestrator (reads CSVs, generates charts)
├── chart_format.py      # Chart templates and rendering
├── chart_definitions.py # Chart-specific configuration (CSV source URL/path)
├── dash_app.py          # Web dashboard server
├── Chart_Images/        # Static PNG output
├── Charts/              # Interactive HTML output
└── requirements.txt     # Python dependencies
```

| Module | Responsibility |
|--------|----------------|
| `main.py` | Reads pre-computed CSVs from Report Library, orchestrates chart generation |
| `chart_format.py` | Defines chart templates, renders Plotly figures, exports PNG and HTML outputs |
| `chart_definitions.py` | Chart-specific configuration: CSV source (GitHub Pages URL or local path) |
| `dash_app.py` | Serves interactive web dashboard with all generated charts |

### Data Flow

```
GitHub Pages (secretsatoshis.github.io/Bitcoin-Report-Library/csv/)
    │
    ▼
main.py  ──►  Reads CSV files (master_metrics_data.csv.gz + chart CSVs)
    │
    ▼
chart_format.py  ──►  Generates Plotly charts
    │
    ├──►  Chart_Images/  (static PNGs)
    ├──►  Charts/        (interactive HTML)
    └──►  dash_app.py    (web dashboard)
```

## Prerequisites

- Python 3.10+
- pip

## Installation

```bash
git clone https://github.com/SecretSatoshis/Bitcoin-Chart-Library.git
cd Bitcoin-Chart-Library

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

By default, Chart Library fetches CSV data directly from the Report Library's GitHub Pages site — no need to clone or run Report Library locally.

The pipeline:
1. Fetches pre-computed data from GitHub Pages (or local path)
2. Generates cycle analysis charts (drawdowns, halvings, cycle lows)
3. Creates monthly and yearly return charts
4. Renders all chart templates as interactive Plotly figures
5. Exports static PNGs to `Chart_Images/`
6. Exports interactive HTML charts to `Charts/`

### Optional: Launch Dashboard

To start the interactive web dashboard, uncomment the last two lines in `main.py`:

```python
app_with_charts = generate_dash_app()
app_with_charts.run_server(debug=True, use_reloader=False, host="0.0.0.0", port=8080)
```

Then visit `http://localhost:8080` in your browser.

## Configuration

### CSV Data Source

By default, the Chart Library reads CSVs from the Report Library's GitHub Pages site:

```
https://secretsatoshis.github.io/Bitcoin-Report-Library/csv/
```

To use a local Report Library instead (for development), set the `REPORT_CSV_DIR` environment variable:

```bash
export REPORT_CSV_DIR=../Bitcoin-Report-Library/csv
python main.py
```

This is configured in `chart_definitions.py`.

### Required CSV Files

The following files are read from the CSV data source (generated daily by Report Library):

| File | Description |
|------|-------------|
| `master_metrics_data.csv.gz` | Complete dataset with all calculated metrics and change calculations (gzipped) |
| `drawdown_data.csv` | ATH drawdown cycles for cycle analysis charts |
| `cycle_low_data.csv` | Market cycle performance from cycle lows |
| `halving_data.csv` | Performance indexed from each Bitcoin halving |

## Outputs

### Static Images
PNG files exported to `Chart_Images/` for use in reports, presentations, and social media.

### Interactive Charts
HTML files exported to `Charts/` for embedding in web pages or standalone viewing.

### Web Dashboard
Optional Dash application at `http://localhost:8080` with all charts accessible through a web interface.

## Dependencies

```
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
dash>=2.14.0
kaleido>=0.2.1
```

**Note:** This project does not require `requests` or `yfinance` — all data fetching is handled by [Bitcoin-Report-Library](https://github.com/SecretSatoshis/Bitcoin-Report-Library).

## License

GPLv3
