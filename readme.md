# Bitcoin Chart Library

Bitcoin visualization and charting platform powering the Secret Satoshis analytics stack. The system delivers interactive dashboards and publication-ready charts for on-chain metrics, valuation models, and cross-asset analysis.

## Features

- **On-Chain Analytics**: Hash rate, difficulty, transaction metrics, UTXO age bands, address activity, miner revenue, and supply dynamics
- **Valuation Models**: Stock-to-Flow, Thermocap, NVT, Realized Price, electric price models, and relative valuation metrics
- **Cycle Analysis**: Drawdown tracking from ATH, halving epoch comparisons, market cycle low indexing
- **Cross-Asset Comparisons**: Correlations with equities, ETFs, commodities, forex, and fiat money supply
- **Performance Tracking**: Rolling returns (MTD, YTD, YoY), CAGR calculations, and historical return heatmaps

## Architecture

```
Bitcoin-Chart-Library/
├── main.py              # Pipeline orchestrator
├── data_format.py       # Data access and feature engineering
├── chart_format.py      # Chart templates and rendering
├── data_definitions.py  # Configuration and constants
├── dash_app.py          # Web dashboard server
├── Chart_Images/        # Static PNG output
├── Charts/              # Interactive HTML output
└── requirements.txt     # Python dependencies
```

| Module | Responsibility |
|--------|----------------|
| `main.py` | Orchestrates end-to-end execution: data ingestion, metric calculation, chart generation, dashboard launch |
| `data_format.py` | Fetches raw data from APIs, normalizes timestamps, engineers features, calculates derived metrics |
| `chart_format.py` | Defines chart templates, renders Plotly figures, exports PNG and HTML outputs |
| `data_definitions.py` | Central configuration: tickers, API settings, reference data, metric templates, constants |
| `dash_app.py` | Serves interactive web dashboard with all generated charts |

## Installation

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# Clone the repository
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

The pipeline executes in sequence:
1. Fetches on-chain data from BRK API
2. Retrieves market data from Yahoo Finance and CoinGecko
3. Calculates derived metrics and valuation models
4. Computes cycle analysis (drawdowns, halvings, cycle lows)
5. Generates all chart figures
6. Exports PNG images to `Chart_Images/`
7. Exports interactive HTML charts to `Charts/`
8. Launches Dash web dashboard at `http://0.0.0.0:8080`

## Data Sources

| Source | Data Type | Endpoint |
|--------|-----------|----------|
| **BRK (Bitview) API** | On-chain metrics, difficulty, supply data | `bitview.space/api` |
| **Yahoo Finance** | Equities, ETFs, indices, commodities, forex | `yfinance` library |
| **CoinGecko** | Altcoin prices, market caps | Public API |

## Configuration

All configuration is centralized in `data_definitions.py`:

- **Tickers**: Asset symbols organized by category (stocks, ETFs, indices, commodities, forex, crypto)
- **Reference Data**: Fiat money supply, precious metals supply, gold allocation breakdown
- **API Settings**: BRK metrics list, endpoint URLs, timeout values
- **Model Parameters**: Electricity costs, trading days, unit conversions
- **Chart Settings**: Analysis columns, moving average metrics

## Outputs

### Static Images
PNG files exported to `Chart_Images/` for use in reports, presentations, and social media.

### Interactive Charts
HTML files exported to `Charts/` for embedding in web pages or standalone viewing.

### Web Dashboard
Live Dash application at `http://0.0.0.0:8080` with all charts accessible through a web interface.

## Dependencies

```
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
dash>=2.14.0
requests>=2.31.0
kaleido>=0.2.1
yfinance>=0.2.36
```

## License

GPLv3
