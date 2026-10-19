"""Keep Bing's previously indexed chart links working after the filename migration."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEXED_LEGACY_PATHS = (
    "/bitcoin_ath_drawdown.html",
    "/bitcoin_1_year_supply.html",
    "/bitcoin_supply_age.html",
    "/bitcoin_active_addresses.html",
    "/bitcoin_halving_cycle.html",
    "/bitcoin_production_price.html",
    "/bitcoin_macro_supply.html",
)


@pytest.mark.parametrize("source", INDEXED_LEGACY_PATHS)
def test_indexed_legacy_links_redirect_directly_to_the_same_current_chart(source):
    config = json.loads((ROOT / "vercel.json").read_text())
    redirects = config["redirects"]
    matches = [rule for rule in redirects if rule["source"] == source]
    assert len(matches) == 1
    rule = matches[0]
    assert rule["permanent"] is True
    destination = rule["destination"]
    assert destination != source
    assert destination.lower() == source
    assert destination not in {item["source"] for item in redirects}
    catalog = json.loads((ROOT / "Charts/catalog.json").read_text())
    assert destination[1:] in {entry["url"] for entry in catalog["charts"]}
    document = (ROOT / "Charts" / destination[1:]).read_text()
    assert f'href="https://charts.secretsatoshis.com{destination}"' in document
