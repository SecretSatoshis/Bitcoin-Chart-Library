# Secret Satoshis Bitcoin Chart Library

A static, searchable library of 46 Bitcoin charts, rendered with **TradingView
Lightweight Charts 5.2.1**. Python prepares verified data and HTML; one shared browser
renderer supplies the Secret Satoshis theme, interactions and PNG exports.

Existing public filenames and `?chart=` catalog links are preserved. No Python
server is required in production, and there are no CDN or Google Fonts dependencies.

## Install and build

```sh
uv sync --locked
uv run --no-sync python main.py
```

The default source is Bitcoin Report Library's published CSV release. For local data:

```sh
uv run --no-sync python main.py --csv-dir ../Bitcoin-Report-Library/csv --serve
```

Open http://127.0.0.1:8767/. The optional server binds only to localhost. Use
`--output outputs/review` to build a separate review pack and `--port` to choose a port.
You can also double-click `Charts/index.html` or any chart HTML. Keep its `assets/`
folder alongside it. Embedded data and local fonts work without HTTP access.

The Report Library manifest binds all inputs by SHA-256, including the candle bundle,
which every release must carry. Daily builds require a completed release within the
existing two-day freshness window, a complete master calendar, and reconciled
report-date prices. Remote reads request the manifest with a cache-busting query and
each file keyed to its release, retrying briefly while GitHub Pages' 10-minute CDN cache
catches up, so files from two releases are never mixed. Builds are staged and validated before
replacing the output pack; errors retain the previous pack. Do not edit generated
`Charts/` files directly.

## Architecture

```text
Report Library release
  → chart_inputs.py: verify one coherent release
  → chart_templates/: discover definitions and website metadata
  → chart_data.py: shared, renderer-independent transformations
  → chart_build.py: compact embedded payloads + content-versioned shared assets
  → Charts/: catalog, standalone HTML, SEO, manifest, runtime and theme
```

Template families are `timeseries` (39 charts), `cycle` (3) and `seasonal` (4).
Monthly/yearly baselines, cycle scaling, mean/median exclusion and leap-day policies
retain the previous calculations. The migration was checked against the old output
for every series, date, finite value and missing observation in all 59 charts.

`web/chart.html`, `web/chart.css` and `web/renderer.js` own the common presentation.
`web/catalog/` holds the catalog source. The pinned runtime and font licenses live
under `web/vendor/` and `web/fonts/`. The builder verifies the vendored checksums.

## Catalog categories

Templates assign each chart to one category. `CATEGORY_ORDER` in
`chart_templates/__init__.py` controls the catalog order; the build generates
filters, chart headings and metadata from these definitions.

| Category | Charts | Focus |
| --- | ---: | --- |
| Price & Trends | 4 | Price, moving averages, purchasing power and volatility |
| Returns & Comparisons | 6 | Bitcoin returns and performance against other assets |
| Cycles & Seasonality | 7 | Halving cycles, drawdowns and monthly/yearly patterns |
| Valuation Models | 6 | On-chain, network, power-law and electricity-cost models |
| Relative Valuation | 4 | Bitcoin's size relative to metals, companies and base money |
| Holder Sentiment | 4 | Holder profitability, spending and conviction |
| Supply | 4 | Issuance, circulating supply and coin age |
| Network Activity | 5 | Addresses, transactions, transfer volume and fees |
| Mining & Security | 6 | Hashrate, difficulty and miner economics |

Electricity Cost belongs to Valuation Models. Counts above describe the current
46-chart collection; adding a template automatically adds its catalog entry.

## Add a chart

Add a dictionary to a module's `CHARTS` list under `chart_templates/`. New modules
are discovered automatically; there is no separate catalog list or hardcoded count.
For example, a new module can contain:

```python
CHARTS = [{
    'filename': 'Bitcoin_New_Comparison',
    'title': 'Bitcoin New Comparison',
    'description': 'A clear description of the comparison, its underlying data, and what a reader can learn.',
    'category': 'Price & Trends',
    'featured': False,
    'family': 'timeseries',
    'data_source': 'Data Source: Bitview',
    'filter_start_date': '2010-07-01',
    'default_range': '4Y',
    'axes': {'right': {'label': 'Bitcoin Price (USD)', 'unit': 'USD', 'mode': 'log'}},
    'y_data': [{'name': 'Bitcoin Price', 'data': 'price_close', 'axis': 'right'}],
}]
```

The filename is a public URL identifier and must be unique. Use an existing report
metric; new economic calculations belong upstream. Add a `left` axis for a second
unit/scale, and assign series accordingly. Optional metrics use `optional: True` and
are visibly disclosed when unavailable. A required metric cannot be silently omitted.

Supported units: `USD`, `percent` (already percentage points), `ratio`, `BTC`,
`BTC/day`, `count`, `hashrate` (source H/s), `sats/USD`, `USD/TH/s/day`.

The halving-cycle chart translates each historical cycle's indexed returns into
USD using the current halving-day closing price. The current cycle therefore
shows its actual price; prior cycles show rescaled comparisons, not forecasts.
The existing `Bitcoin_Halving_Cycle.html` URL is unchanged. Cycle-low comparisons
use the same scaling approach anchored at the current cycle low.

NUPL's lower panel shows labeled sentiment ranges with horizontal boundaries at
0, 0.25, 0.50 and 0.75. These show daily NUPL against the saved ranges; the
dashboard sentiment label continues to use its seven-day average.
Power Law's upper price panel shows shaded valuation ranges bounded by prepared
0.58×, 1×, 1.73× and 3× model curves from Report Library. Hiding the Power Law
model hides its range shading; boundary curves remain individually selectable.
The upper panel keeps its shading without range labels. The lower multiple panel
uses the exact same numeric-range label renderer as NUPL, with dashed horizontal
thresholds and right-aligned range labels, without colored fills or a separate
key. Both track the active price scale; labels hide only when their range is too
narrow to fit, rather than moving to a different horizontal position.
These are the dashboard's fixed reviewed thresholds, not forecast confidence
intervals. Both kinds of range annotations use the same renderer in PNG exports.
Metadata stays in the template; spacing, colors, formatting and export layout stay
in the shared theme. `chart_style.py` defines a contrasting palette and stable
metric identities, with Bitcoin and current-period emphasis in orange. Related
model/multiple pairs share colors across panels, and assets retain their colors
across comparison charts. Use the shared events list when appropriate.

Legends keep Bitcoin (or the current cycle/year) first, then sort remaining
readings from highest to lowest within each panel, with unavailable readings last.
Ordering follows the displayed date during hover and returns to the report date
when the cursor leaves. PNG legends use the same ordering at the report date.

New chart families require a shared transformation and renderer capability; ordinary
new metric combinations do not. Run the build and tests before submitting a template.

## Interaction and export

Ordinary time-series charts start at four years. MTD/YTD comparisons start at the
report period; seasonal views retain the whole normalized month/year. Cycle charts
use actual integer days, not dates disguised as elapsed time.

Desktop dual-axis charts overlay both scales. At 760px and below they use synchronized
panels, unless the template explicitly defines a panel layout. Range, visibility and axis settings survive layout changes. The legend supports
show/hide, Only, Show all, and Remove all (which retains Bitcoin price). Axis controls
are labeled Right and Left. Range buttons include YTD / 1Y / 4Y / 10Y / All;
reset restores defaults. Source values remain precise in the payload.
Null observations split lines; nonpositive values are omitted on logarithmic axes and
remain available in linear mode. Readouts do not forward-fill gaps.

**Stacked panel layouts:** `Bitcoin_Metcalfe_Model` uses the approved stacked layout
on desktop, mobile and in the catalog: price and Any Balance model value above
(65%, log), with the price/model multiple below (35%, linear). Plot height adapts
between 570–710px so the plot fits when its top is scrolled into view, without
reserving space for the controls or page heading. The catalog sends its browser
viewport height through a validated parent/iframe message, so embedded plots use
the same dimensions as standalone pages without iframe height feedback. This also
works in direct-file previews and updates when the window resizes. Fractional-bar ranges stay locked during
scrolling, dragging and zooming, including beyond the ends of the data. Dates and hover are
synchronized; only the lower panel shows date ticks. Event labels appear once in
the upper panel and their lines span both. Price/Multiple scale controls and the
legend follow the panel grouping. PNG exports preserve the split and selected state.
The same 65/35 layout is used for Power Law, Moving Averages, Electricity Cost,
and Volatility. NUPL and Realized Price also use this layout,
and both default to 10 years. Delta Cap is retired. Remaining charts retain their
existing layouts.

NVT Price shows Bitcoin alongside 30-day (blue), 90-day (teal) and 365-day (pink)
valuation models. Report Library smooths BRK transfer volume with each period's
rolling median before applying the two-year median NVT and dividing by current
supply. All three models and matching weekly/monthly observations are prepared
in Report Library; the Chart Library only displays them.
NVT uses the shared 65/35 stacked layout, with price/models above and a linear
price-to-model multiple below. Only the 90-day multiple appears in the lower
panel. A labeled 1.0× reference appears
only in the multiple panel, including PNG exports. Dates and controls remain synchronized.

| Chart | Layout and defaults |
| --- | --- |
| Metcalfe | Price/model above, multiple below; 10 years |
| Power Law | Price/model above, multiple below; 4-year default |
| Bitcoin Price | Existing overlay; all history, monthly price candles on log, market cap line on linear |
| Moving Averages | Price/averages above, 200-day multiple below; 4 years, weekly price candles |
| Electricity Cost | Price, 4¢/6¢ power expense and Hayes model above; Hayes multiple below; 4-year line defaults |
| Satoshis Per Dollar | Satoshis only, single axis; all history |
| Volatility | Price above, both volatility measures below; 4 years, weekly price candles |

Electricity Cost retains the `Bitcoin_Production_Price.html` URL. The separate
`Bitcoin_Electricity_Cost.html` chart is retired; the consolidated chart replaces
the former 5¢ power-expense series with the prepared 4¢ and 6¢ series.

Templates can set `default_presentation: 'candles'` and
`default_interval: 'daily'`, `'weekly'`, or `'monthly'`. Only Bitcoin USD price
becomes candles; other metrics stay lines using prepared interval observations.
Older frozen releases without the requested candle data fall back to daily lines.

In Returns & Comparisons, Bitcoin CAGR and Year-Over-Year Return use stacked
return panels, 10-year defaults and weekly price candles. CAGR vs Other Assets
retains its 4-year view; MTD and YTD asset comparisons retain their existing setup.
Both YTD-by-year charts set `default_hidden_series: ['2017']`. This controls initial
visibility and Reset only: the 2017 data remains in the payload, legend and historical
averages, and readers can reveal it individually or with Show all. MTD-by-year charts
are unchanged.

Supply charts use the following layouts: 1+ Year Supply has price above and the
1+ year share below, with a 10-year default. Supply & Daily Issuance shows issuance
above and circulating supply below, with all history. Macro Supply and Supply Age
Distribution show supply metrics alone on a single linear axis, with all history.

Network Activity: Active Addresses shows all address metrics below price with a
10-year default. Transaction Volume shows all volume metrics below price with a
4-year default. Transaction Fees uses the same split and retains its 4-year default. Address Balance Distribution removes price and shows all history.
Transactions defaults to all history on a linear scale.

Holder Sentiment: SOPR and Supply in Profit vs Loss place their metrics below price.
Reserve Risk uses a lower panel with Bitcoin price alone above. HODL Bank, VOCD
and MVOCD remain calculation inputs without visible lines. Its public filename stays `Bitcoin_HODL_Bank.html`. These
charts retain 4-year defaults. Supply-adjusted Days Destroyed is retired.

Mining & Security: Hash Price, Hash Ribbons, Miner Revenue and Puell Multiple
place their mining metrics below Bitcoin price. Network Difficulty and Hashrate
show only their own metrics, with price removed. All retain their existing scales
and 4-year defaults. The Hashrate URL remains `Bitcoin_Hashrate_Price.html`.

Optional `panels` metadata groups series by their existing axis. List order is display
order; positive `weight` values determine the fixed height proportions. Each axis
must appear exactly once. For example:

```python
'panels': [
    {'axis': 'right', 'label': 'Bitcoin Price & Metcalfe Value',
     'control_label': 'Price', 'weight': 65},
    {'axis': 'left', 'label': 'Price / Metcalfe Value',
     'control_label': 'Multiple', 'weight': 35},
],
```

A template with one axis and one panel uses the full height. Panel metadata never
changes source metrics or calculations. Run `npm run test:panels` after building
to check this pilot's interactions and exports; review images are saved under the
ignored `outputs/metcalfe-panels/` folder.

Every chart has an **Export PNG** button. For a scripted 2400×1350 export:

```sh
npm ci
npx playwright install chromium
node scripts/export-chart.cjs Charts/Bitcoin_YTD_Return_Comparison_full.html outputs/ytd.png
```

The script calls the same compositor as the button, retaining the current range and
visibility and including title, date, legend, source and attribution. PNGs are generated
on demand, not for every chart each day. SVG export is not included.

The stable capture interface is `await window.SecretSatoshisChart.ready`; call
`exportImage(false)` on the resolved object to obtain a PNG data URL. The payload's
`schemaVersion` is 2. Its shared `x` calendar and series `start`/`values` arrays avoid
repeating timestamps per point. `coverage` describes source history independently of
seasonal display dates. `build-manifest.json` records each chart's payload and HTML hash.

## Frozen single-chart export

`chart_build.build_single(csv_dir, filename, output, frozen_report_date=...)` builds one
chart against an earlier Report Library release, for reports that must show data as of a
past cutoff. The explicit `frozen_report_date` must match the release manifest and the
source cutoff; all hashes and price/calendar checks still apply, and only current-release
freshness is replaced by validation against that historical date.

A single export stages its HTML and required shared assets, checks every asset
reference, then moves them beside the requested output; a failure leaves the
destination unchanged. It refuses to write inside the published `Charts/` pack. Capture
the result as a PNG through the same `window.SecretSatoshisChart` interface described
above, with network requests blocked.

## Validation and publication

```sh
uv run --no-sync pytest -q
npm ci
npx playwright install chromium
npm run test:browser
```

Browser tests start their own temporary local server and also open files directly.
They compare plotted data to payloads across the full inventory, exercise representative
mobile charts, catalog embeds, axes and PNG exports, and save inspection artifacts
under ignored `outputs/browser-checks/`. Linux CI installs Chromium with `--with-deps`.

The scheduled GitHub workflow checks hourly (at :45) whether the Report Library has
published a release newer than the one the committed pack was built from
(`scripts/release-status.py`). GitHub starts scheduled jobs hours late and in no
guaranteed order, so a fixed offset after the Report Library could chart the previous
release for a whole day. When a new release exists the workflow validates it, builds
the complete pack, runs Python and browser checks, and only then uploads the artifact
for publication; otherwise it stops after the check. A failed build is retried by the
next hourly run. Pull requests check the committed pack. Browser dependencies
are pinned in `package-lock.json`; they are not needed to generate HTML locally.

The original 59-URL inventory is retained in `tests/fixtures/original-chart-inventory.json`
as a migration record. `tests/fixtures/retired-chart-inventory.json` lists intentional
removals; the catalog check still requires every other original chart. New templates
may increase the count.

Everything is static and retains the current Vercel/GitHub output structure. Hashed
runtime/style filenames are immutable; unversioned assets (favicon, logo, license
texts) are cached for a day; HTML and catalog data revalidate. Git history
retains the previous implementation and generated release for rollback. Production
changes must be pushed only after review and explicit authorization.

### Bitcoin candles

Charts with an actual `price_close` USD series offer **Bitcoin: Line / Candles** and
**Daily / Weekly / Monthly** intervals. Line remains the default. Rising candles use muted green and falling candles muted
red, with orange retained for the Bitcoin price line. Weekly/monthly
views use the producer's exact period-end metric observations, not recalculated
indicators. Their unfinished final period is labeled and capped at the report date.

The Report Library publishes `bitcoin_candles.csv.gz`, `weekly_metrics_data.csv.gz`,
and `monthly_metrics_data.csv.gz` in its checksum manifest. This repository only
validates/selects those prepared observations and renders them; it never fetches BRK
or aggregates OHLC. The bundle is a required input: a release without it, or with an
inconsistent bundle, fails validation.

`SecretSatoshisChart.setPresentation('candles', 'monthly')` selects the presentation
for both the browser and common PNG compositor. `exportChart` also accepts
`{presentation: 'candles', interval: 'monthly'}`. Run the focused candle check with
`node scripts/check-candles.cjs`; it fails if a Bitcoin price chart has no candle views.

## Shared dashboard presentation

The Report Library dashboard vendors this same renderer using
`scripts/sync-dashboard.py ../Bitcoin-Report-Library/dashboard/static/shared-chart`.
Run it after shared presentation changes; it records source checksums, removes
obsolete hashed renderer/style versions, and writes the dashboard's model line colors
and historical events to `components/chart-colors.json` and `components/chart-events.json`. Commit the generated dashboard assets in
the Report Library as part of the same release. The dashboard defaults to weekly
candles and a linear scale, with scenario cards above the plot and PNG. No chart draws
gridlines.
Standalone chart pages retain their own template defaults and site navigation/footer;
the catalog embeds the same chart in a matching-width viewer.

The dashboard uses three synced frames: price outlook, MTD and YTD. Each frame accepts
data only from its same-origin parent for its own chart ID, reports its height, and posts
a ready or error message once `SecretSatoshisChart.ready` resolves. `source-manifest.json`
records the frames and the hash of every source and synced asset. Seasonal payloads with
numeric days use `xAxisLabel` and show only the All range.
