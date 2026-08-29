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

# Charts are served identically from charts.secretsatoshis.com and from the
# underlying GitHub Pages path. Only the custom domain is canonical, so every
# generated page names it explicitly.
CANONICAL_BASE = "https://charts.secretsatoshis.com"
SOCIAL_IMAGE = "https://secretsatoshis.com/assets/images/social-card.jpg"
SITE_NAME = "Secret Satoshis"
CODE_LICENSE = "https://www.gnu.org/licenses/gpl-3.0.html"
SOURCE_REPOSITORY = "https://github.com/SecretSatoshis/Bitcoin-Chart-Library"

HEAD_MARKER_OPEN = "<!-- ss:head -->"
HEAD_MARKER_CLOSE = "<!-- /ss:head -->"
BODY_MARKER_OPEN = "<!-- ss:heading -->"
BODY_MARKER_CLOSE = "<!-- /ss:heading -->"
NOSCRIPT_MARKER_OPEN = "<!-- ss:chart-index -->"
NOSCRIPT_MARKER_CLOSE = "<!-- /ss:chart-index -->"

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
        "series": ["Month-to-date return", "Historical years"],
    },
    "Bitcoin_MTD_Return_By_Month_Indexed": {
        "title": "Bitcoin MTD Returns, Indexed",
        "series": ["Indexed Bitcoin price", "Median", "Average"],
    },
    "Bitcoin_YTD_Return_By_Year_Percentage": {
        "title": "Bitcoin YTD Returns by Year",
        "series": ["Year-to-date return", "Historical years"],
    },
    "Bitcoin_YTD_Return_By_Year_Indexed": {
        "title": "Bitcoin YTD Returns, Indexed",
        "series": ["Indexed Bitcoin price", "Median", "Average"],
    },
}

DESCRIPTION_OVERRIDES = {
    # Term, then definition. Each entry feeds the page meta description,
    # og:description, the JSON-LD Dataset.description and the catalog card,
    # so it must make sense quoted on its own.

    # --- Price Models ---
    "Bitcoin_Promo": (
        "An orientation chart pairing Bitcoin's price with realized price, "
        "the 200-week moving average, hashrate and the 32x thermocap band."
    ),
    "Bitcoin_Electricity_Cost": (
        "Bitcoin's electricity cost of production, the power expense of "
        "mining one coin, modelled across tariffs from $0.03 to $0.07 per "
        "kWh."
    ),
    "Bitcoin_Metcalfe_Model": (
        "The Metcalfe model values a network in proportion to the square of "
        "its users, estimated here from address counts above four balance "
        "thresholds."
    ),
    "Bitcoin_Power_Law_Model": (
        "The power law model fits Bitcoin's price to a straight line on a "
        "log-log scale against time, treating growth as a function of "
        "network age."
    ),
    "Bitcoin_Price": (
        "Bitcoin's price and market capitalisation in US dollars, from the "
        "earliest exchange data through the most recent daily close."
    ),
    "Bitcoin_Price_Chart_MA": (
        "Bitcoin's price against its 7, 50 and 200-day and 200-week moving "
        "averages, with the multiple of price to the 200-day average."
    ),
    "Bitcoin_Production_Price": (
        "Bitcoin's cost of production, combining the power expense of "
        "mining a coin with the Hayes cost-of-production network price."
    ),
    "Bitcoin_S2F_Price": (
        "Stock-to-flow values Bitcoin by the ratio of existing supply to "
        "annual new issuance, a scarcity measure that steps up at each "
        "halving."
    ),
    "Bitcoin_Volatility": (
        "Bitcoin's realised volatility, the annualised standard deviation "
        "of daily returns, measured over rolling 30-day and 180-day "
        "windows."
    ),
    "Bitcoin_Sats_Per_Dollar": (
        "Satoshis per dollar expresses Bitcoin's price inverted: how many "
        "of the smallest units, one hundred-millionth of a coin, one dollar "
        "buys."
    ),

    # --- On-chain Valuation ---
    "Bitcoin_Delta_Cap": (
        "Delta cap is realized cap minus average cap, a long-term valuation "
        "floor derived from the difference between on-chain and lifetime "
        "average pricing."
    ),
    "Bitcoin_NVT_Price": (
        "NVT price values Bitcoin from the value settled on-chain, applying "
        "the network-value-to-transactions ratio in reverse to imply a fair "
        "price."
    ),
    "Bitcoin_NUPL": (
        "Net Unrealized Profit/Loss is the total paper gain or loss held "
        "across all circulating supply, expressed as a share of market "
        "capitalisation."
    ),
    "Bitcoin_On_Chain": (
        "A composite of Bitcoin's on-chain valuation models: realized price "
        "and its cohorts, the Hayes network price, and the 200-week moving "
        "average."
    ),
    "Bitcoin_Realized_Price": (
        "Realized price is the average on-chain acquisition cost of all "
        "circulating coins, valuing each at the price it last moved rather "
        "than today's."
    ),
    "Bitcoin_Thermocap_Multiples": (
        "Thermocap is the cumulative value paid to miners since genesis; "
        "thermocap price divides it by supply to give a security-spend "
        "valuation floor."
    ),

    # --- Asset Comparisons ---
    "Bitcoin_Gold": (
        "Bitcoin's market capitalisation set against gold and silver, with "
        "gold broken into jewellery, private investment, official holdings "
        "and industrial use."
    ),
    "Bitcoin_M0": (
        "Bitcoin's market capitalisation set against the M0 base money "
        "supply of nine major economies, from the United States and China "
        "to Australia."
    ),
    "Bitcoin_Equities": (
        "Bitcoin's market capitalisation set against the world's largest "
        "listed companies, spanning technology, energy, finance and "
        "Bitcoin-linked equities."
    ),

    # --- Relative Valuation ---
    "Bitcoin_RV": (
        "Bitcoin's price if its market capitalisation matched each of ten "
        "reference assets, from silver and gold to Apple, NVIDIA and US "
        "base money."
    ),
    "Bitcoin_RV_Sector_Leaders": (
        "Bitcoin's price if its market capitalisation matched a "
        "cross-sector leader: Tesla, Eli Lilly, Saudi Aramco or SpaceX."
    ),
    "Bitcoin_RV_Financials": (
        "Bitcoin's price if its market capitalisation matched a major "
        "financial or payments firm: Berkshire Hathaway, JPMorgan, Visa, "
        "PayPal or Block."
    ),
    "Bitcoin_RV_M0": (
        "Bitcoin's price if its market capitalisation matched the M0 base "
        "money supply of the United Kingdom, Japan, China, the United "
        "States or the EU."
    ),
    "Bitcoin_RV_metals": (
        "Bitcoin's price if its market capitalisation matched silver or "
        "gold, with gold split into private investment, official holdings "
        "and the total market."
    ),
    "Bitcoin_RV_Semiconductors": (
        "Bitcoin's price if its market capitalisation matched a leading "
        "semiconductor firm: NVIDIA, Broadcom, TSMC, Samsung Electronics or "
        "Micron."
    ),
    "Bitcoin_RV_stocks": (
        "Bitcoin's price if its market capitalisation matched a mega-cap "
        "technology company: Meta, Amazon, Alphabet, Microsoft or Apple."
    ),

    # --- Cycle Analysis ---
    "Bitcoin_ATH_Drawdown": (
        "Bitcoin's drawdowns from each all-time high, aligned at the peak "
        "so the depth and duration of all five cycles can be compared "
        "directly."
    ),
    "Bitcoin_Halving_Cycle": (
        "Bitcoin's price performance indexed from each halving, aligning "
        "the 2012, 2016, 2020 and 2024 eras from the day issuance last "
        "halved."
    ),
    "Bitcoin_Cycle_Low": (
        "Bitcoin's price performance indexed from each cycle low, aligning "
        "six market cycles from the day the bear market bottomed."
    ),

    # --- Returns and Performance ---
    "Bitcoin_CAGR": (
        "Bitcoin's four-year compound annual growth rate, the annualised "
        "return an investor would have earned over any rolling four-year "
        "holding period."
    ),
    "Bitcoin_CAGR_Comparison": (
        "Four-year compound annual growth rates for Bitcoin and eight "
        "benchmarks, covering equities, technology, financials, gold, "
        "bonds, the dollar and miners."
    ),
    "Bitcoin_MTD_Return_By_Month_Indexed": (
        "Bitcoin's month-to-date return path for every year since 2014, "
        "indexed to the current month so each year's shape can be compared "
        "day by day."
    ),
    "MTD_Return_By_Year_Percentage": (
        "Bitcoin's month-to-date return for every calendar year since 2014, "
        "shown as a daily percentage alongside the median and average "
        "across years."
    ),
    "Bitcoin_YTD_Return_By_Year_Indexed": (
        "Bitcoin's year-to-date return path for every year since 2014, "
        "indexed to the current year so each year's shape can be compared "
        "day by day."
    ),
    "Bitcoin_YTD_Return_By_Year_Percentage": (
        "Bitcoin's year-to-date return for every calendar year since 2014, "
        "shown as a daily percentage alongside the median and average "
        "across years."
    ),
    "Bitcoin_MTD_Return_Comparison": (
        "Month-to-date returns for Bitcoin and eight benchmarks, covering "
        "equities, technology, financials, gold, bonds, the dollar and "
        "Bitcoin miners."
    ),
    "Bitcoin_YOY_Return_Comparison": (
        "Bitcoin's year-over-year return, the percentage change in price "
        "against the same date twelve months earlier, plotted against price "
        "itself."
    ),
    "Bitcoin_YTD_Return_Comparison": (
        "Year-to-date returns for Bitcoin and eight benchmarks, covering "
        "equities, technology, financials, gold, bonds, the dollar and "
        "Bitcoin miners."
    ),
    "Bitcoin_YTD_Return_Comparison_full": (
        "Year-to-date returns for Bitcoin and sixteen benchmarks: US and "
        "international equities, sector funds, commodities, bonds and "
        "Bitcoin-linked stocks."
    ),

    # --- Supply ---
    "Bitcoin_1_Year_Supply": (
        "One-year active supply is the share of circulating Bitcoin that "
        "has moved at least once in the past year, the mirror of "
        "long-dormant coins."
    ),
    "Bitcoin_Macro_Supply": (
        "Bitcoin's supply split by liquidity and holding period, separating "
        "liquid from illiquid coins and short-term from long-term holder "
        "balances."
    ),
    "Bitcoin_Supply": (
        "Bitcoin's circulating supply against daily new issuance, the coins "
        "created by each block subsidy, smoothed over 30-day and 365-day "
        "windows."
    ),
    "Bitcoin_Supply_Age": (
        "Bitcoin's supply grouped by how recently each coin last moved, "
        "from under one month to over ten years, showing the distribution "
        "of holding periods."
    ),

    # --- Network Activity ---
    "Bitcoin_Address_Balance": (
        "The number of Bitcoin addresses holding at least a given balance, "
        "across thirteen thresholds from a single satoshi to ten thousand "
        "coins."
    ),
    "Bitcoin_Active_Addresses": (
        "Active addresses count the distinct Bitcoin addresses sending or "
        "receiving in a day, a measure of network use smoothed over 30 and "
        "365 days."
    ),
    "Bitcoin_Transaction_Fee": (
        "Total Bitcoin transaction fees paid to miners each day in US "
        "dollars, the portion of miner revenue that does not come from the "
        "block subsidy."
    ),
    "Bitcoin_Transaction_Value": (
        "Bitcoin transaction volume is the total value settled on-chain "
        "each day, smoothed over 30-day and 365-day windows to show the "
        "underlying trend."
    ),
    "Bitcoin_Transactions": (
        "The number of Bitcoin transactions confirmed each day, with 30-day "
        "and 365-day moving averages to separate short-term noise from the "
        "trend."
    ),

    # --- Mining and Security ---
    "Bitcoin_Hash_Price": (
        "Hash price is miner revenue per terahash per second per day, the "
        "dollar income a unit of mining hardware earns and the core measure "
        "of mining economics."
    ),
    "Bitcoin_Hash_Ribbons": (
        "Hash ribbons compare Bitcoin's 30-day and 60-day hashrate "
        "averages; their crossover marks miner capitulation and the "
        "recovery that follows."
    ),
    "Bitcoin_Hashrate": (
        "Hashrate is the total computing power securing the Bitcoin "
        "network, smoothed over 30-day and 365-day windows to see through "
        "short-term variance."
    ),
    "Bitcoin_Miner_Revenue": (
        "Total daily miner revenue in US dollars, the block subsidy plus "
        "transaction fees, smoothed over 30-day and 365-day windows."
    ),
    "Bitcoin_Difficulty": (
        "Mining difficulty is the target the network adjusts roughly every "
        "two weeks to hold block times near ten minutes as hashrate "
        "changes."
    ),
    "Bitcoin_Hashrate_Price": (
        "Bitcoin's price against the total hashrate securing the network, "
        "with 30-day and 365-day averages of the computing power committed "
        "to mining."
    ),
    "Bitcoin_Puell_Multiple": (
        "The Puell Multiple divides the daily dollar value of newly issued "
        "coins by its own 365-day average, measuring miner revenue against "
        "its norm."
    ),

    # --- Holder Behavior ---
    "Bitcoin_Adjusted_BDD": (
        "Bitcoin Days Destroyed weights each coin moved by how long it sat "
        "still; adjusting for circulating supply makes the measure "
        "comparable across eras."
    ),
    "Bitcoin_HODL_Bank": (
        "HODL Bank accumulates the opportunity cost borne by long-term "
        "holders; reserve risk divides price by it to gauge conviction "
        "against price."
    ),
    "Bitcoin_SOPR": (
        "Spent Output Profit Ratio compares the value of coins when spent "
        "to their value when acquired, with 1.0 marking the aggregate "
        "break-even line."
    ),
    "Bitcoin_Supply_Profit_Loss": (
        "The share of circulating Bitcoin last moved below and above the "
        "current price, splitting total supply into coins held in profit "
        "and in loss."
    ),

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


def _chart_coverage(chart_path: Path, latest_data_date: str) -> str | None:
    """The dates this chart actually plots, not an assumed platform-wide range.

    Google requires Dataset markup to describe the page it is on. Charts start
    anywhere from 2010 to the current month, so a shared start date would be
    false on most of them.
    """
    document = chart_path.read_text(encoding="utf-8")
    dates = re.findall(r'"x":\["(\d{4}-\d{2}-\d{2})', document)
    if not dates:
        return None
    # The seasonality pages normalize every historical trace onto the current
    # calendar month or year. Their x values therefore all begin in the current
    # year even though the trace names identify observations back to 2014.
    if chart_path.stem in SPECIAL_CHARTS:
        years = [int(value) for value in re.findall(r'"name":"(\d{4})"', document)]
        if years:
            return f"{min(years):04d}-01-01/{latest_data_date}"
    return f"{min(dates)}/{latest_data_date}"


def _head_block(entry: dict, latest_data_date: str, coverage: str | None) -> str:
    """Search and social metadata for one standalone chart page."""
    title = entry["title"]
    description = entry["description"]
    canonical = f"{CANONICAL_BASE}/{entry['url']}"
    esc = html.escape
    structured = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": title,
        "description": description,
        "url": canonical,
        "keywords": entry.get("tags", []),
        "isAccessibleForFree": True,
        "dateModified": latest_data_date,
        "creator": {
            "@type": "Organization",
            "name": SITE_NAME,
            "url": "https://secretsatoshis.com/",
        },
        # The chart and the code that draws it are GPL-3.0. The underlying
        # market data is third-party and keeps its publishers' terms, so the
        # licence is declared on the source code rather than on the dataset.
        "isBasedOn": {
            "@type": "SoftwareSourceCode",
            "name": "Bitcoin Chart Library",
            "codeRepository": SOURCE_REPOSITORY,
            "license": CODE_LICENSE,
        },
        "isPartOf": {
            "@type": "DataCatalog",
            "name": "Secret Satoshis Bitcoin Chart Library",
            "url": f"{CANONICAL_BASE}/",
        },
    }
    if coverage:
        structured["temporalCoverage"] = coverage
    return "\n".join(
        [
            HEAD_MARKER_OPEN,
            f'<title>{esc(title)} | {SITE_NAME}</title>',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f'<meta name="description" content="{esc(description, quote=True)}">',
            f'<link rel="canonical" href="{esc(canonical, quote=True)}">',
            '<meta name="robots" content="index, follow, max-image-preview:large">',
            f'<meta property="og:title" content="{esc(title, quote=True)} | {SITE_NAME}">',
            f'<meta property="og:description" content="{esc(description, quote=True)}">',
            f'<meta property="og:url" content="{esc(canonical, quote=True)}">',
            '<meta property="og:type" content="website">',
            f'<meta property="og:site_name" content="{SITE_NAME}">',
            f'<meta property="og:image" content="{SOCIAL_IMAGE}">',
            '<meta property="og:image:alt" content="Secret Satoshis — '
            'AI-Native Bitcoin Market Intelligence">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{SOCIAL_IMAGE}">',
            '<meta name="theme-color" content="#08080c">',
            '<link rel="icon" href="assets/favicon.png" type="image/png" sizes="180x180">',
            '<link rel="apple-touch-icon" href="assets/favicon.png">',
            '<script type="application/ld+json">'
            + json.dumps(structured, separators=(",", ":"))
            + "</script>",
            HEAD_MARKER_CLOSE,
        ]
    )


def _heading_block(entry: dict, latest_data_date: str) -> str:
    """A visible caption on the standalone chart page.

    These pages previously carried a title and 31 characters of visible text
    wrapped around half a megabyte of Plotly JSON — nothing for a reader or a
    crawler to work with. The caption states what the chart is, when the data
    ends, and how to get back to the library.

    It is rendered above the chart, sized to sit quietly under the plot's own
    title when the page is embedded in the catalog viewer.
    """
    esc = html.escape
    return "\n".join(
        [
            BODY_MARKER_OPEN,
            '<div class="ss-caption">',
            f'  <h1>{esc(entry["title"])}</h1>',
            f'  <p>{esc(entry["description"])}</p>',
            f'  <p class="ss-meta">{esc(entry["category"])} · data through '
            f'<time datetime="{latest_data_date}">{latest_data_date}</time> · '
            f'<a href="{CANONICAL_BASE}/">Secret Satoshis Chart Library</a></p>',
            "</div>",
            "<style>",
            ".ss-caption{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;",
            "max-width:70ch;margin:0 auto;padding:20px 24px 4px;color:#9090a8;}",
            ".ss-caption h1{margin:0 0 8px;font-size:15px;font-weight:600;color:#e4e4ef;}",
            ".ss-caption p{margin:0 0 6px;font-size:12.5px;line-height:1.6;font-weight:300;}",
            ".ss-caption .ss-meta{color:#5a5a74;font-size:11.5px;}",
            ".ss-caption a{color:#F7931A;text-underline-offset:3px;}",
            "</style>",
            BODY_MARKER_CLOSE,
        ]
    )


def _replace_between(document: str, opener: str, closer: str, block: str) -> str | None:
    if opener in document and closer in document:
        pattern = re.escape(opener) + r".*?" + re.escape(closer)
        return re.sub(pattern, lambda _: block, document, count=1, flags=re.DOTALL)
    return None


def _ensure_document_head(chart_path: Path, entry: dict, latest_data_date: str) -> None:
    """Inject search, social and structured metadata into one chart page.

    Idempotent: a rebuild replaces the previous block rather than appending a
    second one, so this is safe to run on every build.
    """
    document = chart_path.read_text(encoding="utf-8")
    original = document

    if "<head>" not in document:
        raise ValueError(f"Chart has no <head> element: {chart_path}")

    document = re.sub(
        r"<html(?![^>]*\blang=)([^>]*)>", r'<html lang="en"\1>', document, count=1
    )

    head_block = _head_block(entry, latest_data_date, _chart_coverage(chart_path, latest_data_date))
    replaced = _replace_between(document, HEAD_MARKER_OPEN, HEAD_MARKER_CLOSE, head_block)
    if replaced is not None:
        document = replaced
    else:
        # Plotly writes its own <title>; drop it so ours is the only one.
        document = re.sub(
            r"<title>.*?</title>", "", document, count=1, flags=re.IGNORECASE | re.DOTALL
        )
        document = document.replace("</head>", head_block + "</head>", 1)

    heading_block = _heading_block(entry, latest_data_date)
    replaced = _replace_between(document, BODY_MARKER_OPEN, BODY_MARKER_CLOSE, heading_block)
    if replaced is not None:
        document = replaced
    elif "<body>" in document:
        document = document.replace("<body>", "<body>\n" + heading_block, 1)

    if document != original:
        chart_path.write_text(document, encoding="utf-8")


def _write_catalog_head(output_dir: Path, catalog: dict) -> None:
    """Social tags and DataCatalog structured data for the library index."""
    index_path = output_dir / "index.html"
    if not index_path.is_file():
        return
    structured = {
        "@context": "https://schema.org",
        "@type": "DataCatalog",
        "name": "Secret Satoshis Bitcoin Chart Library",
        "description": (
            f"{catalog['chart_count']} interactive Bitcoin charts covering price, "
            "on-chain activity, supply, mining, network activity and valuation."
        ),
        "url": f"{CANONICAL_BASE}/",
        "dateModified": catalog["latest_data_date"],
        "isAccessibleForFree": True,
        "creator": {
            "@type": "Organization",
            "name": SITE_NAME,
            "url": "https://secretsatoshis.com/",
        },
        "dataset": [
            {
                "@type": "Dataset",
                "name": entry["title"],
                "description": entry["description"],
                "url": f"{CANONICAL_BASE}/{entry['url']}",
            }
            for entry in catalog["charts"]
        ],
    }
    block = "\n".join(
        [
            HEAD_MARKER_OPEN,
            f'<meta property="og:type" content="website">',
            f'<meta property="og:site_name" content="{SITE_NAME}">',
            f'<meta property="og:title" content="Bitcoin Chart Library | {SITE_NAME}">',
            '<meta property="og:description" content="'
            + html.escape(structured["description"], quote=True) + '">',
            f'<meta property="og:url" content="{CANONICAL_BASE}/">',
            f'<meta property="og:image" content="{SOCIAL_IMAGE}">',
            '<meta property="og:image:alt" content="Secret Satoshis — '
            'AI-Native Bitcoin Market Intelligence">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{SOCIAL_IMAGE}">',
            '<script type="application/ld+json">'
            + json.dumps(structured, separators=(",", ":"))
            + "</script>",
            HEAD_MARKER_CLOSE,
        ]
    )
    document = index_path.read_text(encoding="utf-8")
    replaced = _replace_between(document, HEAD_MARKER_OPEN, HEAD_MARKER_CLOSE, block)
    if replaced is None:
        replaced = document.replace("</head>", block + "\n</head>", 1)
    if replaced != document:
        index_path.write_text(replaced, encoding="utf-8")


def _write_sitemap(output_dir: Path, catalog: dict) -> None:
    """Emit sitemap.xml from the validated catalog entries."""
    lastmod = catalog["latest_data_date"]
    urls = [(f"{CANONICAL_BASE}/", "1.0")]
    urls += [(f"{CANONICAL_BASE}/{entry['url']}", "0.8") for entry in catalog["charts"]]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, priority in urls:
        lines += ["  <url>",
                  f"    <loc>{loc}</loc>",
                  f"    <lastmod>{lastmod}</lastmod>",
                  "    <changefreq>daily</changefreq>",
                  f"    <priority>{priority}</priority>",
                  "  </url>"]
    lines.append("</urlset>")
    (output_dir / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_robots(output_dir: Path) -> None:
    """Emit robots.txt.

    Every crawler is allowed, including AI retrieval, user-initiated fetch and
    training agents. That is deliberate, not an omission: the platform is
    GPL-3.0 and its promise is that the work can be inspected and reused.
    """
    (output_dir / "robots.txt").write_text(
        "\n".join(
            [
                "# All crawlers welcome, including AI retrieval and training agents.",
                "# Deliberate: this public, GPL-3.0 chart library permits crawling.",
                "User-agent: *",
                "Allow: /",
                "",
                f"Sitemap: {CANONICAL_BASE}/sitemap.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_noscript_index(output_dir: Path, catalog: dict) -> None:
    """Render a crawlable link list into the catalog's existing noscript block.

    The catalog grid is built client-side from catalog.json, so without this the
    served HTML contains no link to any chart.
    """
    index_path = output_dir / "index.html"
    if not index_path.is_file():
        return
    items = "\n".join(
        "\n".join(
            [
                "          <li>",
                f'            <a href="{entry["url"]}">{html.escape(entry["title"])}</a>',
                f'            <span>{html.escape(entry["description"])}</span>',
                f'            <em>{html.escape(entry["category"])}</em>',
                "          </li>",
            ]
        )
        for entry in catalog["charts"]
    )
    block = "\n".join(
        [
            NOSCRIPT_MARKER_OPEN,
            f'        <ul class="chart-index">',
            items,
            "        </ul>",
            NOSCRIPT_MARKER_CLOSE,
        ]
    )
    document = index_path.read_text(encoding="utf-8")
    replaced = _replace_between(
        document, NOSCRIPT_MARKER_OPEN, NOSCRIPT_MARKER_CLOSE, block
    )
    if replaced is None:
        anchor = "</noscript>"
        if anchor not in document:
            return
        replaced = document.replace(anchor, block + "\n      " + anchor, 1)
    if replaced != document:
        index_path.write_text(replaced, encoding="utf-8")


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

    for entry in entries:
        _ensure_document_head(
            generated[entry["filename"]], entry, catalog["latest_data_date"]
        )
    _write_sitemap(output_dir, catalog)
    _write_robots(output_dir)
    _write_noscript_index(output_dir, catalog)
    _write_catalog_head(output_dir, catalog)

    return catalog
