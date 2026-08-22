"""Generate the static Secret Satoshis chart catalog from chart definitions."""

from __future__ import annotations

import html
import json
import re
import shutil
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_CHART_COUNT = 59

CATEGORY_FILES = OrderedDict(
    [
        (
            "Price Models",
            [
                "Bitcoin_Price",
                "Bitcoin_Price_Chart_MA",
                "Bitcoin_Sats_Per_Dollar",
                "Bitcoin_Volatility",
                "Bitcoin_Promo",
                "Bitcoin_Production_Price",
                "Bitcoin_Electricity_Cost",
                "Bitcoin_Power_Law_Model",
                "Bitcoin_Metcalfe_Model",
                "Bitcoin_S2F_Price",
            ],
        ),
        (
            "On-chain Valuation",
            [
                "Bitcoin_Thermocap_Multiples",
                "Bitcoin_Realized_Price",
                "Bitcoin_Delta_Cap",
                "Bitcoin_NVT_Price",
                "Bitcoin_NUPL",
                "Bitcoin_On_Chain",
            ],
        ),
        (
            "Asset Comparisons",
            ["Bitcoin_Gold", "Bitcoin_Equities", "Bitcoin_M0"],
        ),
        (
            "Relative Valuation",
            [
                "Bitcoin_RV_metals",
                "Bitcoin_RV_stocks",
                "Bitcoin_RV_Semiconductors",
                "Bitcoin_RV_Financials",
                "Bitcoin_RV_Sector_Leaders",
                "Bitcoin_RV_M0",
                "Bitcoin_RV",
            ],
        ),
        (
            "Cycle Analysis",
            [
                "Bitcoin_ATH_Drawdown",
                "Bitcoin_Cycle_Low",
                "Bitcoin_Halving_Cycle",
            ],
        ),
        (
            "Returns and Performance",
            [
                "Bitcoin_YOY_Return_Comparison",
                "Bitcoin_CAGR",
                "Bitcoin_CAGR_Comparison",
                "Bitcoin_MTD_Return_Comparison",
                "Bitcoin_YTD_Return_Comparison",
                "Bitcoin_YTD_Return_Comparison_full",
                "MTD_Return_By_Year_Percentage",
                "Bitcoin_MTD_Return_By_Month_Indexed",
                "Bitcoin_YTD_Return_By_Year_Percentage",
                "Bitcoin_YTD_Return_By_Year_Indexed",
            ],
        ),
        (
            "Supply",
            [
                "Bitcoin_Supply",
                "Bitcoin_Macro_Supply",
                "Bitcoin_1_Year_Supply",
                "Bitcoin_Supply_Age",
            ],
        ),
        (
            "Network Activity",
            [
                "Bitcoin_Transactions",
                "Bitcoin_Transaction_Fee",
                "Bitcoin_Transaction_Value",
                "Bitcoin_Active_Addresses",
                "Bitcoin_Address_Balance",
            ],
        ),
        (
            "Mining and Security",
            [
                "Bitcoin_Hashrate",
                "Bitcoin_Hashrate_Price",
                "Bitcoin_Hash_Ribbons",
                "Bitcoin_Difficulty",
                "Bitcoin_Hash_Price",
                "Bitcoin_Miner_Revenue",
                "Bitcoin_Puell_Multiple",
            ],
        ),
        (
            "Holder Behavior",
            [
                "Bitcoin_Adjusted_BDD",
                "Bitcoin_HODL_Bank",
                "Bitcoin_SOPR",
                "Bitcoin_Supply_Profit_Loss",
            ],
        ),
    ]
)

SPECIAL_CHARTS = {
    "MTD_Return_By_Year_Percentage": {
        "title": "Bitcoin MTD Returns by Year",
        "description": "Compares daily month-to-date Bitcoin returns across calendar years.",
        "series": ["Month-to-date return", "Historical years"],
    },
    "Bitcoin_MTD_Return_By_Month_Indexed": {
        "title": "Bitcoin MTD Returns Indexed to Current Month",
        "description": "Compares historical month-to-date Bitcoin paths indexed to the current month.",
        "series": ["Indexed Bitcoin price", "Median", "Average"],
    },
    "Bitcoin_YTD_Return_By_Year_Percentage": {
        "title": "Bitcoin YTD Returns by Year",
        "description": "Compares daily year-to-date Bitcoin returns across calendar years.",
        "series": ["Year-to-date return", "Historical years"],
    },
    "Bitcoin_YTD_Return_By_Year_Indexed": {
        "title": "Bitcoin YTD Returns Indexed to Current Year",
        "description": "Compares historical year-to-date Bitcoin paths indexed to the current year.",
        "series": ["Indexed Bitcoin price", "Median", "Average"],
    },
}

DESCRIPTION_OVERRIDES = {
    "Bitcoin_ATH_Drawdown": "Compares the depth and duration of Bitcoin drawdowns from successive all-time highs.",
    "Bitcoin_Cycle_Low": "Compares Bitcoin performance indexed from the low of each configured market cycle.",
    "Bitcoin_Halving_Cycle": "Compares Bitcoin performance indexed from each halving across completed and current eras.",
}

FEATURED_FILES = {
    "Bitcoin_Price",
    "Bitcoin_Price_Chart_MA",
    "Bitcoin_Supply",
    "Bitcoin_Hashrate",
    "Bitcoin_Realized_Price",
    "Bitcoin_Power_Law_Model",
    "Bitcoin_RV",
    "Bitcoin_Cycle_Low",
}

TAG_RULES = OrderedDict(
    [
        ("marketcap", "market cap"),
        ("price", "price"),
        ("moving average", "moving averages"),
        ("satoshi", "satoshis"),
        ("volatility", "volatility"),
        ("supply", "supply"),
        ("transaction", "transactions"),
        ("fee", "fees"),
        ("address", "addresses"),
        ("hash ribbon", "hash ribbons"),
        ("hash rate", "hashrate"),
        ("hashrate", "hashrate"),
        ("difficulty", "difficulty"),
        ("miner", "miners"),
        ("thermocap", "thermocap"),
        ("realized", "realized price"),
        ("nvt", "NVT"),
        ("nupl", "NUPL"),
        ("profit", "profit and loss"),
        ("electric", "energy"),
        ("power law", "power law"),
        ("metcalfe", "Metcalfe"),
        ("stock-to-flow", "stock-to-flow"),
        ("gold", "gold"),
        ("equity", "equities"),
        ("m0", "money supply"),
        ("return", "returns"),
        ("cagr", "CAGR"),
        ("drawdown", "drawdowns"),
        ("halving", "halving"),
        ("cycle", "cycles"),
    ]
)


def _date_string(value) -> str:
    if hasattr(value, "date"):
        value = value.date()
    return str(value)[:10]


def _series_names(template: dict) -> list[str]:
    names: list[str] = []
    for series in template.get("y_data", []):
        name = str(series.get("name", "")).strip()
        if name and name not in names:
            names.append(name)
    return names


def _natural_join(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _description(filename: str, series: list[str]) -> str:
    if filename in DESCRIPTION_OVERRIDES:
        return DESCRIPTION_OVERRIDES[filename]
    if not series:
        return "An interactive Bitcoin research chart from the Secret Satoshis library."
    if len(series) <= 3:
        return f"Tracks {_natural_join(series)} over time."
    return f"Compares {series[0]} with {len(series) - 1} related series over time."


def _tags(title: str, category: str, series: list[str]) -> list[str]:
    haystack = " ".join([title, category, *series]).casefold()
    tags: list[str] = []
    seen: set[str] = set()
    for needle, tag in TAG_RULES.items():
        normalized_tag = tag.casefold()
        if needle in haystack and normalized_tag not in seen:
            tags.append(tag)
            seen.add(normalized_tag)
        if len(tags) == 5:
            break
    if not tags:
        tags.append("Bitcoin")
    return tags


def _chart_height(chart_path: Path, fallback: int | None = None) -> int:
    with chart_path.open(encoding="utf-8") as handle:
        prefix = handle.read(30_000)
    match = re.search(r'class="plotly-graph-div" style="height:(\d+)px;', prefix)
    return int(match.group(1)) if match else (fallback or 700)


def _ensure_document_title(chart_path: Path, title: str) -> None:
    document = chart_path.read_text(encoding="utf-8")
    title_markup = f"<title>{html.escape(title)} | Secret Satoshis</title>"
    if re.search(r"<title>.*?</title>", document, flags=re.IGNORECASE | re.DOTALL):
        updated = re.sub(
            r"<title>.*?</title>",
            title_markup,
            document,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
    elif "</head>" in document:
        updated = document.replace("</head>", f"{title_markup}</head>", 1)
    else:
        raise ValueError(f"Chart has no <head> element: {chart_path}")
    if updated != document:
        chart_path.write_text(updated, encoding="utf-8")


def build_chart_catalog(
    *,
    report_date,
    chart_templates: list[dict],
    cycle_templates: list[dict],
    output_dir: str | Path = "Charts",
    logo_path: str | Path = "Secret_Satoshis_Logo.png",
) -> dict:
    """Write catalog.json and validate all standalone chart outputs."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "assets").mkdir(parents=True, exist_ok=True)

    metadata = {
        template["filename"]: {
            "title": template["title"],
            "series": _series_names(template),
            "height": template.get("height"),
        }
        for template in [*chart_templates, *cycle_templates]
    }
    metadata.update(SPECIAL_CHARTS)

    categorized = [filename for files in CATEGORY_FILES.values() for filename in files]
    if len(categorized) != EXPECTED_CHART_COUNT or len(set(categorized)) != len(categorized):
        raise ValueError("The category registry must contain 59 unique chart filenames.")

    generated = {
        path.stem: path
        for path in output_dir.glob("*.html")
        if path.name != "index.html"
    }
    if set(categorized) != set(generated):
        missing = sorted(set(categorized) - set(generated))
        uncataloged = sorted(set(generated) - set(categorized))
        raise ValueError(
            f"Chart/catalog mismatch. Missing outputs: {missing}; "
            f"uncataloged outputs: {uncataloged}"
        )

    entries: list[dict] = []
    for category, filenames in CATEGORY_FILES.items():
        for filename in filenames:
            chart_metadata = metadata.get(filename)
            if not chart_metadata:
                raise ValueError(f"No source metadata found for {filename}")
            title = chart_metadata["title"]
            series = chart_metadata.get("series", [])
            description = chart_metadata.get("description") or _description(filename, series)
            _ensure_document_title(generated[filename], title)
            entries.append(
                {
                    "title": title,
                    "filename": filename,
                    "url": f"{filename}.html",
                    "category": category,
                    "description": description,
                    "tags": _tags(title, category, series),
                    "featured": filename in FEATURED_FILES,
                    "height": _chart_height(generated[filename], chart_metadata.get("height")),
                }
            )

    shutil.copy2(logo_path, output_dir / "assets" / "logo.png")
    category_order = {category: index for index, category in enumerate(CATEGORY_FILES)}
    entries.sort(key=lambda entry: (category_order[entry["category"]], entry["title"]))
    catalog = {
        "title": "Bitcoin Chart Library",
        "latest_data_date": _date_string(report_date),
        "chart_count": len(entries),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "categories": list(CATEGORY_FILES),
        "charts": entries,
    }
    (output_dir / "catalog.json").write_text(
        json.dumps(catalog, indent=2) + "\n", encoding="utf-8"
    )
    return catalog
