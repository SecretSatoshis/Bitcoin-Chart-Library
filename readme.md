# Secret Satoshis Bitcoin Chart Library

A static, searchable library of 50 Bitcoin charts, rendered with **TradingView
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

The Report Library manifest binds all inputs by SHA-256. Daily builds require a
completed release within the existing two-day freshness window, a complete master
calendar, and reconciled report-date prices. Builds are staged and validated before
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

Template families are `timeseries` (43 charts), `cycle` (3) and `seasonal` (4).
Monthly/yearly baselines, cycle scaling, mean/median exclusion and leap-day policies
retain the previous calculations. The migration was checked against the old output
for every series, date, finite value and missing observation in all 59 charts.

`web/chart.html`, `web/chart.css` and `web/renderer.js` own the common presentation.
`web/catalog/` holds the catalog source. The pinned runtime and font licenses live
under `web/vendor/` and `web/fonts/`. The builder verifies the vendored checksums.

## Add a chart

Add a dictionary to a module's `CHARTS` list under `chart_templates/`. New modules
are discovered automatically; there is no separate catalog list or hardcoded count.
For example, a new module can contain:

```python
CHARTS = [{
    'filename': 'Bitcoin_New_Comparison',
    'title': 'Bitcoin New Comparison',
    'description': 'A clear description of the comparison, its underlying data, and what a reader can learn.',
    'category': 'Price Models',
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
`BTC/day`, `BTC-days`, `count`, `hashrate` (source H/s), `sats/USD`, `USD/TH/s/day`.
Metadata stays in the template; spacing, colors, formatting and export layout stay
in the shared theme. Colors derive from stable metric identities, with Bitcoin and
current-period emphasis in orange. Use the shared events list when appropriate.

New chart families require a shared transformation and renderer capability; ordinary
new metric combinations do not. Run the build and tests before submitting a template.

## Interaction and export

Ordinary time-series charts start at four years. MTD/YTD comparisons start at the
report period; seasonal views retain the whole normalized month/year. Cycle charts
use actual integer days, not dates disguised as elapsed time.

Desktop dual-axis charts overlay both scales. At 760px and below they use synchronized
panels. Range, visibility and axis settings survive layout changes. The legend supports
show/hide, Only, Show all, and Remove all (which retains Bitcoin price). Axis controls
are labeled Right and Left. Range buttons include YTD / 1Y / 4Y / 10Y / All;
reset restores defaults. Source values remain precise in the payload.
Null observations split lines; nonpositive values are omitted on logarithmic axes and
remain available in linear mode. Readouts do not forward-fill gaps.

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

## Quarterly newsletter integration

The Newsletter Pipeline's quarterly YTD scripts now use `chart_build.build_single`
and the shared browser export interface. They retain the public source URL and PNG
filename. A frozen export requires an explicit `frozen_report_date`, matching the
manifest and source cutoff; all hashes and price/calendar checks still apply. Only
current-release freshness is replaced by validation against that historical cutoff.

A single export writes its HTML plus required shared assets beside it. The pipeline's
existing Dashboard Playwright runtime can capture it with network requests blocked.
Coordinate the Chart Library and Newsletter Pipeline updates in the same approved
cutover: the new caller needs the new producer API.

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

The daily GitHub workflow keeps its 01:30 UTC schedule. It validates the release,
builds the complete pack, runs Python and browser checks, and only then uploads the
artifact for publication. Pull requests check the committed pack. Browser dependencies
are pinned in `package-lock.json`; they are not needed to generate HTML locally.

The original 59-URL inventory is retained in `tests/fixtures/original-chart-inventory.json`
as a migration record. `tests/fixtures/retired-chart-inventory.json` lists intentional
removals; the catalog check still requires every other original chart. New templates
may increase the count.

Everything is static and retains the current Vercel/GitHub output structure. Hashed
runtime/style filenames are immutable; HTML and catalog data revalidate. Git history
retains the previous implementation and generated release for rollback. Production
changes must be pushed only after review and explicit authorization.

### Optional Bitcoin candles

Charts with an actual `price_close` USD series offer **Bitcoin: Line / Candles** and
**Daily / Weekly / Monthly** intervals. Line remains the default. Rising candles use muted green and falling candles muted
red, with orange retained for the Bitcoin price line. Weekly/monthly
views use the producer's exact period-end metric observations, not recalculated
indicators. Their unfinished final period is labeled and capped at the report date.

The Report Library publishes `bitcoin_candles.csv.gz`, `weekly_metrics_data.csv.gz`,
and `monthly_metrics_data.csv.gz` in its checksum manifest. This repository only
validates/selects those prepared observations and renders them; it never fetches BRK
or aggregates OHLC. Legacy releases without the entire optional bundle remain
line-only; a partially supplied or inconsistent bundle fails validation.

`SecretSatoshisChart.setPresentation('candles', 'monthly')` selects the presentation
for both the browser and common PNG compositor. `exportChart` also accepts
`{presentation: 'candles', interval: 'monthly'}`. Run the focused optional-feature
check with `node scripts/check-candles.cjs`. Publish the Report Library producer
before enabling these controls in a new Chart Library release.

## Shared dashboard presentation

The Report Library dashboard vendors this same renderer using
`scripts/sync-dashboard.py ../Bitcoin-Report-Library/dashboard/static/shared-chart`.
Run it after shared presentation changes; it records source checksums and removes
obsolete hashed renderer/style versions. Commit the generated dashboard assets in
the Report Library as part of the same release. The dashboard defaults to weekly
candles, a linear scale and no gridlines, with scenario cards above the plot and PNG.
Standalone chart pages retain their own template defaults and site navigation/footer;
the catalog embeds the same chart in a matching-width viewer.
