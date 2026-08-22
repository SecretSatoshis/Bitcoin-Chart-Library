import html
import json
import re
from pathlib import Path

import plotly.graph_objects as go

import chart_format as charts
from chart_catalog import CATEGORY_FILES, EXPECTED_CHART_COUNT, SPECIAL_CHARTS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHARTS_DIR = PROJECT_ROOT / "Charts"


def _catalog():
    return json.loads((CHARTS_DIR / "catalog.json").read_text(encoding="utf-8"))


def test_catalog_has_exactly_the_complete_generated_chart_pack():
    catalog = _catalog()
    entries = catalog["charts"]
    cataloged = {entry["filename"] for entry in entries}
    generated = {
        path.stem for path in CHARTS_DIR.glob("*.html") if path.name != "index.html"
    }
    registered = {
        filename for filenames in CATEGORY_FILES.values() for filename in filenames
    }

    assert catalog["chart_count"] == EXPECTED_CHART_COUNT
    assert len(entries) == EXPECTED_CHART_COUNT
    assert len(cataloged) == EXPECTED_CHART_COUNT
    assert cataloged == generated == registered


def test_every_catalog_entry_has_valid_metadata_and_standalone_output():
    catalog = _catalog()
    categories = set(catalog["categories"])

    assert catalog["categories"] == [
        "Price Models",
        "On-chain Valuation",
        "Asset Comparisons",
        "Relative Valuation",
        "Cycle Analysis",
        "Returns and Performance",
        "Supply",
        "Network Activity",
        "Mining and Security",
        "Holder Behavior",
    ]
    assert list(CATEGORY_FILES) == catalog["categories"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", catalog["latest_data_date"])

    for entry in catalog["charts"]:
        expected_url = f'{entry["filename"]}.html'
        chart_path = CHARTS_DIR / expected_url

        assert entry["title"].strip()
        assert entry["description"].strip()
        assert entry["category"] in categories
        assert entry["tags"]
        assert isinstance(entry["featured"], bool)
        assert entry["height"] >= 520
        assert entry["url"] == expected_url
        assert chart_path.is_file()

        chart_document = chart_path.read_text(encoding="utf-8")
        expected_title = (
            f'<title>{html.escape(entry["title"])} | Secret Satoshis</title>'
        )
        assert expected_title in chart_document
        assert 'src="plotly.min.js"' in chart_document


def test_source_metadata_covers_every_registered_chart():
    source_filenames = {template["filename"] for template in charts.chart_templates}
    source_filenames.update(
        template["filename"]
        for template in [charts.chart_drawdowns, charts.chart_cycle_lows, charts.chart_halvings]
    )
    source_filenames.update(SPECIAL_CHARTS)
    registered = {
        filename for filenames in CATEGORY_FILES.values() for filename in filenames
    }

    assert source_filenames == registered


def test_catalog_page_contains_only_one_unloaded_iframe():
    document = (CHARTS_DIR / "index.html").read_text(encoding="utf-8")
    iframe_tags = re.findall(r"<iframe\b[^>]*>", document, flags=re.IGNORECASE)

    assert len(iframe_tags) == 1
    assert not re.search(r"\bsrc\s*=", iframe_tags[0], flags=re.IGNORECASE)
    assert (
        document.index('id="categoryFilters"')
        < document.index('id="viewer"')
        < document.index('id="chartGroups"')
    )
    assert 'id="chartFrameWrap" tabindex="0"' in document
    assert "Swipe or scroll horizontally" in document
    assert 'fetch(\'catalog.json\'' in (CHARTS_DIR / "assets/catalog.js").read_text(
        encoding="utf-8"
    )


def test_vercel_config_serves_the_static_directory_with_safe_cache_boundaries():
    config = json.loads((CHARTS_DIR / "vercel.json").read_text(encoding="utf-8"))
    headers = {rule["source"]: rule["headers"] for rule in config["headers"]}

    assert config["buildCommand"] is None
    assert config["outputDirectory"] == "."
    assert "/plotly.min.js" in headers
    assert "/catalog.json" in headers
    assert "/:chart.html" in headers
    assert "max-age=604800" in headers["/plotly.min.js"][0]["value"]
    assert "max-age=0" in headers["/catalog.json"][0]["value"]
    assert "max-age=0" in headers["/:chart.html"][0]["value"]


def test_chart_export_adds_a_meaningful_document_title(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    figure = go.Figure()
    figure.update_layout(title="Bitcoin Test Metric")

    charts.save_chart_html(figure, "Bitcoin_Test_Metric")

    document = (tmp_path / "Charts/Bitcoin_Test_Metric.html").read_text(
        encoding="utf-8"
    )
    assert "<title>Bitcoin Test Metric | Secret Satoshis</title>" in document
    assert 'src="plotly.min.js"' in document
