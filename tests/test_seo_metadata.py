"""Regression tests for generated SEO and structured-data output.

Everything these cover is machine-generated on every build, which means it can
drift without anyone noticing. Each assertion here corresponds to a defect that
was found by hand and would otherwise be found by hand again.
"""

from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path

import pytest

from chart_catalog import CANONICAL_BASE, EXPECTED_CHART_COUNT

CHARTS = Path(__file__).resolve().parents[1] / "Charts"
CATALOG = json.loads((CHARTS / "catalog.json").read_text(encoding="utf-8"))
ENTRIES = CATALOG["charts"]
PAGES = {e["filename"]: (CHARTS / e["url"]).read_text(encoding="utf-8") for e in ENTRIES}


def _ld(document: str) -> dict:
    match = re.search(r'application/ld\+json">(.*?)</script>', document, re.S)
    assert match, "no JSON-LD block"
    return json.loads(match.group(1))


def test_catalog_covers_every_chart():
    assert len(ENTRIES) == EXPECTED_CHART_COUNT


def test_titles_and_descriptions_are_unique():
    titles = [e["title"] for e in ENTRIES]
    descriptions = [e["description"] for e in ENTRIES]
    assert len(set(titles)) == len(titles), "duplicate chart title"
    assert len(set(descriptions)) == len(descriptions), "duplicate description"


def test_titles_fit_a_search_result():
    suffix = len(" | Secret Satoshis")
    too_long = [e["title"] for e in ENTRIES if len(e["title"]) + suffix > 62]
    assert not too_long, f"titles truncate in search: {too_long}"


def test_titles_carry_no_hardcoded_year():
    current = str(date.today().year)
    stale = [e["title"] for e in ENTRIES if current in e["title"]]
    assert not stale, f"titles bake in a year and will go stale: {stale}"


def test_descriptions_are_a_usable_length():
    bad = [(e["filename"], len(e["description"])) for e in ENTRIES
           if not 70 <= len(e["description"]) <= 160]
    assert not bad, f"descriptions outside 70-160 chars: {bad}"


@pytest.mark.parametrize("filename", sorted(PAGES))
def test_every_page_has_one_canonical_on_the_custom_domain(filename):
    document = PAGES[filename]
    canonicals = re.findall(r'<link rel="canonical" href="([^"]+)"', document)
    assert len(canonicals) == 1, f"{filename}: {len(canonicals)} canonical tags"
    assert canonicals[0] == f"{CANONICAL_BASE}/{filename}.html"


@pytest.mark.parametrize("filename", sorted(PAGES))
def test_every_page_has_one_title_and_one_h1(filename):
    document = PAGES[filename]
    assert len(re.findall(r"<title>", document)) == 1
    assert len(re.findall(r"<h1[ >]", document)) == 1


@pytest.mark.parametrize("filename", sorted(PAGES))
def test_social_tags_are_complete(filename):
    document = PAGES[filename]
    for tag in ('property="og:title"', 'property="og:description"',
                'property="og:image"', 'property="og:image:alt"',
                'property="og:url"', 'name="twitter:card"'):
        assert tag in document, f"{filename}: missing {tag}"
    assert len(re.findall(r'name="twitter:card"', document)) == 1


@pytest.mark.parametrize("filename", sorted(PAGES))
def test_structured_data_is_valid_and_accurate(filename):
    data = _ld(PAGES[filename])
    assert data["@type"] == "Dataset"
    assert data["url"] == f"{CANONICAL_BASE}/{filename}.html"
    assert data["dateModified"] == CATALOG["latest_data_date"]
    # The licence belongs to the code, not to third-party market data.
    assert "license" not in data, "Dataset must not claim a licence over upstream data"
    assert data["isBasedOn"]["@type"] == "SoftwareSourceCode"
    assert "codeRepository" in data["isBasedOn"]
    assert "codeRepository" not in data, "codeRepository is not a Dataset property"


def test_temporal_coverage_matches_the_plotted_data():
    """A shared start date would be false on most charts; check a real one."""
    for entry in ENTRIES:
        document = PAGES[entry["filename"]]
        plotted = re.findall(r'"x":\["(\d{4}-\d{2}-\d{2})', document)
        coverage = _ld(document).get("temporalCoverage")
        if not plotted:
            continue
        assert coverage, f"{entry['filename']}: plotted dates but no temporalCoverage"
        expected_start = min(plotted)
        historical_years = [
            int(value) for value in re.findall(r'"name":"(\d{4})"', document)
        ]
        if historical_years:
            expected_start = f"{min(historical_years):04d}-01-01"
        assert coverage.split("/")[0] == expected_start, (
            f"{entry['filename']}: declared start {coverage} != plotted {min(plotted)}"
        )


def test_sitemap_lists_the_catalog_and_every_chart_and_no_fragments():
    sitemap = (CHARTS / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    assert len(locs) == len(ENTRIES) + 1
    assert f"{CANONICAL_BASE}/" in locs
    assert not [u for u in locs if "#" in u], "sitemaps must list canonical documents"
    assert all(u.startswith(CANONICAL_BASE) for u in locs)
    assert f"<lastmod>{CATALOG['latest_data_date']}</lastmod>" in sitemap


def test_robots_allows_crawling_and_points_at_the_sitemap():
    robots = (CHARTS / "robots.txt").read_text(encoding="utf-8")
    assert "Allow: /" in robots
    assert f"Sitemap: {CANONICAL_BASE}/sitemap.xml" in robots


def test_favicon_assets_referenced_by_generated_pages_exist():
    assert (CHARTS / "assets" / "favicon.png").is_file()
    assert (CHARTS / "favicon.ico").is_file()

    documents = [(CHARTS / "index.html").read_text(encoding="utf-8"), *PAGES.values()]
    for document in documents:
        for relative in re.findall(r'<link[^>]+href="(assets/[^"]+)"', document):
            path = relative.split("?", 1)[0]
            assert (CHARTS / path).is_file(), relative


def test_catalog_page_is_crawlable_without_javascript():
    index = (CHARTS / "index.html").read_text(encoding="utf-8")
    block = re.search(r"ss:chart-index(.*?)/ss:chart-index", index, re.S)
    assert block, "no static chart index"
    links = re.findall(r'href="([^"]+)"', block.group(1))
    assert len(links) == len(ENTRIES)
    # Names alone give a crawler nothing; descriptions are the content.
    rendered = html.unescape(block.group(1))
    for entry in ENTRIES:
        assert entry["description"] in rendered, entry["filename"]
        assert entry["category"] in rendered


def test_catalog_page_declares_a_datacatalog():
    index = (CHARTS / "index.html").read_text(encoding="utf-8")
    data = _ld(index)
    assert data["@type"] == "DataCatalog"
    assert len(data["dataset"]) == len(ENTRIES)
    assert data["dateModified"] == CATALOG["latest_data_date"]
