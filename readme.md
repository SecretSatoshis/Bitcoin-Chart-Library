# Bitcoin Chart Library

Bitcoin visualization and charting platform powering the Secret Satoshis analytics stack. The system delivers interactive dashboards and publication-ready charts for on-chain metrics, valuation models, and cross-asset analysis. The generated charts are viewable at [charts.secretsatoshis.com](https://charts.secretsatoshis.com/).

**This is a visualization layer.** [Bitcoin-Report-Library](https://github.com/SecretSatoshis/Bitcoin-Report-Library) handles source-data collection and base metric calculation. This project reads its pre-computed CSV files, performs chart-specific filtering and return/index transformations, and generates the visual outputs. It does not call market-data APIs directly.

## Features

- **On-Chain Analytics**: Hash rate, difficulty, transaction metrics, UTXO age bands, address activity, miner revenue, and supply dynamics
- **Valuation Models**: Stock-to-Flow, Thermocap, NVT, Realized Price, power-law, Metcalfe, electricity-tariff, and relative-value models
- **Cycle Analysis**: Drawdown tracking from ATH, halving epoch comparisons, market cycle low indexing
- **Cross-Asset Comparisons**: Bitcoin comparisons with equities, sector leaders, metals, major market ETFs, and fiat money supply
- **Performance Tracking**: MTD, YTD, and YoY comparisons plus CAGR charts
- **Searchable Static Catalog**: Lightweight filters and search across all 59 charts, with one on-demand chart viewer
- **Interactive Dashboard**: Scrollable web-based Dash view for the template-driven chart set

## Architecture

```
Bitcoin-Chart-Library/
├── main.py              # Pipeline orchestrator (reads CSVs, generates charts)
├── chart_format.py      # Chart templates and rendering
├── chart_catalog.py     # Catalog metadata, validation, and JSON generation
├── chart_definitions.py # Chart-specific configuration (CSV source URL/path)
├── dash_app.py          # Web dashboard server
├── Charts/              # Static catalog, standalone HTML charts, and shared assets
├── tests/               # Regression tests
├── pyproject.toml       # Python 3.12 dependency contract
├── uv.lock              # Exact reproducible dependency graph
├── requirements.txt     # Legacy runtime-install mirror
└── requirements-dev.txt # Legacy runtime and test mirror
```

| Module | Responsibility |
|--------|----------------|
| `main.py` | Reads pre-computed CSVs from Report Library, orchestrates chart generation |
| `chart_format.py` | Defines chart templates, renders Plotly figures, exports interactive HTML outputs |
| `chart_catalog.py` | Categorizes all 59 outputs, validates complete coverage, and generates `catalog.json` |
| `chart_definitions.py` | Chart-specific configuration: CSV source (GitHub Pages URL or local path) |
| `dash_app.py` | Serves the template-driven Plotly figures on one scrollable page |

### Data Flow

```
Report Library CSVs (GitHub Pages or REPORT_CSV_DIR)
    │
    ▼
main.py  ──►  Reads master, drawdown, cycle-low, and halving CSVs
    │
    ▼
chart_format.py  ──►  Generates titled Plotly HTML figures
    │
    ├──►  chart_catalog.py  ──►  searchable catalog and validated metadata
    ├──►  Charts/           (catalog, standalone HTML pack, and shared assets)
    └──►  dash_app.py  (optional template-chart dashboard)
```

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
git clone https://github.com/SecretSatoshis/Bitcoin-Chart-Library.git
cd Bitcoin-Chart-Library

# Create the Python 3.12 environment from the reviewed lockfile
uv sync --locked
```

## Usage

```bash
uv run --no-sync python main.py
```

By default, Chart Library fetches CSV data directly from the Report Library's GitHub Pages site — no need to clone or run Report Library locally.

The pipeline:
1. Reads pre-computed data from GitHub Pages or a local directory
2. Generates three cycle-analysis charts
3. Generates four monthly and yearly return-comparison charts
4. Renders 52 configured chart templates as Plotly figures
5. Exports the complete 59-chart HTML pack to `Charts/`
6. Validates every chart against the category registry and generates `Charts/catalog.json`

### Preview the Complete HTML Pack

After generating the charts, serve the repository from a second terminal:

```bash
uv run --no-sync python -m http.server 8765
```

Open `http://localhost:8765/Charts/` to access every generated chart. This is a
lightweight searchable catalog. Selecting a card loads only that chart in the embedded
viewer; **Open standalone** preserves direct access to each existing chart URL.

### Optional: Launch Dashboard

To place the template-driven charts on one scrollable page, set `SERVE_DASH=1`:

```bash
SERVE_DASH=1 python main.py
```

Then visit `http://localhost:8080` in your browser. The current dashboard contains
the 52 figures produced from `chart_templates`; the seven special cycle and return
charts remain available as individual HTML files in `Charts/`. Add `DASH_DEBUG=1`
to enable Dash's debug mode while developing.

The server binds to `127.0.0.1` and is opt-in by environment variable rather than by
editing `main.py`, because a committed `app.run()` call blocks forever and prevents CI
from ever reaching its commit step.

## Configuration

### CSV Data Source

By default, the Chart Library reads CSVs from the Report Library's GitHub Pages site:

```
https://secretsatoshis.github.io/Bitcoin-Report-Library/csv/
```

To use a local Report Library instead (for development), set the `REPORT_CSV_DIR` environment variable:

```bash
REPORT_CSV_DIR=../Bitcoin-Report-Library/csv python main.py
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

Required chart metrics raise an error when absent. A metric explicitly marked
`optional` in a chart template emits a warning and is skipped without stopping the
rest of the chart pack.

## Outputs

### Interactive Charts

HTML files exported to `Charts/` for embedding in web pages or standalone viewing. The
standalone chart documents use the bundled `Charts/plotly.min.js`, and branding images
are embedded directly in each document, so viewing them does not require third-party
network requests.

### Static Catalog

`Charts/index.html` reads the generated `Charts/catalog.json` and provides accessible
search, category filters, and deep links such as
`http://localhost:8765/Charts/?chart=Bitcoin_Price` during local preview and
`https://charts.secretsatoshis.com/?chart=Bitcoin_Price` when deployed. The landing page
contains one initially unloaded iframe, so it never downloads all 59 chart documents at
once. Catalog metadata is generated from the chart definitions and the seven special
cycle and return chart registrations rather than a separate hand-written page. On narrow
screens, the catalog keeps dense charts readable in a horizontally scrollable viewer.

### Web Dashboard

Optional Dash application at `http://localhost:8080` with the 52 template-driven
charts displayed on one scrollable page.

## Deployment

The static catalog is designed for a Vercel project connected to this repository with:

- **Production branch:** `main`
- **Framework preset:** Other
- **Root directory:** `Charts`
- **Build command:** None
- **Output directory:** `.`
- **Custom domain:** `charts.secretsatoshis.com`

`Charts/vercel.json` records the no-build static output and cache policy. Standalone
chart HTML and `catalog.json` revalidate immediately, while the shared Plotly runtime
uses a longer browser cache. Each successful chart-update workflow commits `Charts/`
to `main`, which supplies the next production deployment after the repository is linked
in Vercel.

The scheduled chart workflow starts daily at **01:30 UTC**, after the Report Library's
00:30 UTC data-refresh workflow has had time to validate and publish its CSV outputs.
The workflow then runs the chart regression suite, rebuilds the complete chart pack,
and commits the generated `Charts/` files. Both workflows can also be started manually
through GitHub Actions.

## Dependencies

Pinned canonically in `pyproject.toml` and `uv.lock` (and mirrored in
`requirements.txt` for legacy installers):

```
pandas==3.0.5
numpy==2.5.2
plotly==6.6.0
dash==4.0.0
```

**Note:** This project does not depend directly on `requests` or `yfinance`. Pandas
reads pre-computed Report Library CSVs from either the configured local directory or
the default GitHub Pages URL.

## Testing

Install the development dependencies and run the regression suite:

```bash
uv sync --locked
uv run --no-sync pytest -q
```

The suite verifies that all 59 generated charts are cataloged, every catalog URL exists,
no legacy output remains listed, and each standalone document has a meaningful title.

## License

GPLv3
