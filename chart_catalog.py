"""Catalog and search metadata generated from the same payloads as each chart."""
from collections import OrderedDict
import html
import json
import re
from pathlib import Path
from chart_templates import CATEGORY_ORDER

CANONICAL_BASE = "https://charts.secretsatoshis.com"
SOCIAL_IMAGE = "https://secretsatoshis.com/assets/images/chart-library-social-card.jpg"
SITE_NAME = "Secret Satoshis"
ORGANIZATION_ID = "https://secretsatoshis.com/#organization"
CATALOG_DESCRIPTION = (
    "Explore interactive Bitcoin charts covering price, valuation, ETF flows, "
    "network activity, supply, and market cycles."
)
SOCIAL_IMAGE_ALT = (
    "Bitcoin Chart Library: interactive charts covering price, valuation, "
    "ETF flows, network activity, supply, and market cycles."
)
CODE_LICENSE = "https://www.gnu.org/licenses/gpl-3.0.html"
SOURCE_REPOSITORY = "https://github.com/SecretSatoshis/Bitcoin-Chart-Library"

HEAD_MARKER_OPEN = "<!-- ss:head -->"
HEAD_MARKER_CLOSE = "<!-- /ss:head -->"
NOSCRIPT_MARKER_OPEN = "<!-- ss:chart-index -->"
NOSCRIPT_MARKER_CLOSE = "<!-- /ss:chart-index -->"

def _social_tags(title: str, description: str, canonical: str) -> list[str]:
    """Use the same complete social fields for the catalog and chart pages."""
    esc = html.escape
    return [
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:title" content="{esc(title, quote=True)}">',
        f'<meta property="og:description" content="{esc(description, quote=True)}">',
        f'<meta property="og:url" content="{esc(canonical, quote=True)}">',
        f'<meta property="og:image" content="{SOCIAL_IMAGE}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{SOCIAL_IMAGE_ALT}">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:site" content="@SecretSatoshis">',
        '<meta name="twitter:creator" content="@SecretSatoshis">',
        f'<meta name="twitter:title" content="{esc(title, quote=True)}">',
        f'<meta name="twitter:description" content="{esc(description, quote=True)}">',
        f'<meta name="twitter:image" content="{SOCIAL_IMAGE}">',
        f'<meta name="twitter:image:alt" content="{SOCIAL_IMAGE_ALT}">',
    ]

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

def _head_block(entry: dict, latest_data_date: str, coverage: str | None) -> str:
    """Search and social metadata for one standalone chart page."""
    title = entry["title"]
    description = entry["description"]
    canonical = f"{CANONICAL_BASE}/{entry['url']}"
    esc = html.escape
    structured = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": f"{canonical}#dataset",
        "name": title,
        "description": description,
        "url": canonical,
        "keywords": entry.get("tags", []),
        "isAccessibleForFree": True,
        "dateModified": latest_data_date,
        "creator": {
            "@type": "Organization",
            "@id": ORGANIZATION_ID,
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
            "@id": f"{CANONICAL_BASE}/#catalog",
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
            '<script defer src="assets/analytics.js?v=1"></script>',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f'<meta name="description" content="{esc(description, quote=True)}">',
            f'<link rel="canonical" href="{esc(canonical, quote=True)}">',
            '<meta name="robots" content="index, follow, max-image-preview:large">',
            *_social_tags(f"{title} | {SITE_NAME}", description, canonical),
            '<meta name="theme-color" content="#08080c">',
            '<link rel="icon" href="assets/favicon.png" type="image/png" sizes="180x180">',
            '<link rel="apple-touch-icon" href="assets/favicon.png">',
            '<script type="application/ld+json">'
            + json.dumps(structured, separators=(",", ":"))
            + "</script>",
            HEAD_MARKER_CLOSE,
        ]
    )

def _replace_between(document: str, opener: str, closer: str, block: str) -> str | None:
    if opener in document and closer in document:
        pattern = re.escape(opener) + r".*?" + re.escape(closer)
        return re.sub(pattern, lambda _: block, document, count=1, flags=re.DOTALL)
    return None

def _write_catalog_head(output_dir: Path, catalog: dict) -> None:
    """Social tags and DataCatalog structured data for the library index."""
    index_path = output_dir / "index.html"
    if not index_path.is_file():
        return
    structured = {
        "@context": "https://schema.org",
        "@type": "DataCatalog",
        "@id": f"{CANONICAL_BASE}/#catalog",
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
            "@id": ORGANIZATION_ID,
            "name": SITE_NAME,
            "url": "https://secretsatoshis.com/",
        },
        "dataset": [
            {
                "@type": "Dataset",
                "@id": f"{CANONICAL_BASE}/{entry['url']}#dataset",
                "name": entry["title"],
                "description": entry["description"],
                "url": f"{CANONICAL_BASE}/{entry['url']}",
                "creator": {"@id": ORGANIZATION_ID},
            }
            for entry in catalog["charts"]
        ],
    }
    block = "\n".join(
        [
            HEAD_MARKER_OPEN,
            '<script defer src="assets/analytics.js?v=1"></script>',
            *_social_tags(f"Bitcoin Chart Library | {SITE_NAME}", CATALOG_DESCRIPTION, f"{CANONICAL_BASE}/"),
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
            '        <ul class="chart-index">',
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


def catalog_from_payloads(payloads):
    categories = sorted({p['category'] for p in payloads}, key=lambda c: (CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else len(CATEGORY_ORDER),c))
    entries = [{'title':p['title'],'filename':p['id'],'url':p['id']+'.html',
                'category':p['category'],'description':p['description'],
                'tags':_tags(p['title'],p['category'],[s['name'] for s in p['series']]),
                'featured':p['featured'],'height':760,'coverage':p['coverage'],
                'order':p.get('catalogOrder')} for p in payloads]
    # Within a category, charts with a catalog_order come first in that order; the rest by title.
    entries.sort(key=lambda e:(categories.index(e['category']),e['order'] is None,e['order'] or 0,e['title']))
    for entry in entries:
        del entry['order']
    dates = {p['reportDate'] for p in payloads}
    if len(dates) != 1:
        raise ValueError('Catalog charts must share one release date')
    return {'title':'Bitcoin Chart Library','latest_data_date':dates.pop(),
            'chart_count':len(entries),'categories':categories,'charts':entries}


def _write_llms(output_dir: Path, catalog: dict) -> None:
    """Agent discovery map from the maintained catalog, without copied market values."""
    lines = [
        f"# {catalog['title']}",
        "",
        f"> {CATALOG_DESCRIPTION}",
        "",
        f"Catalog data through {catalog['latest_data_date']}. Individual series can have different coverage and gaps; consult each chart's definition and observation dates.",
        "",
        "## Library and data",
        "",
        f"- [Chart Library]({CANONICAL_BASE}/): searchable interactive Bitcoin charts.",
        f"- [Chart catalog]({CANONICAL_BASE}/catalog.json): chart titles, descriptions, categories, tags, URLs, and historical coverage.",
        f"- [Chart sitemap]({CANONICAL_BASE}/sitemap.xml): the library and every standalone chart page.",
        f"- [Source code]({SOURCE_REPOSITORY}): chart definitions, calculations, and the catalog generator.",
        "- [Source data](https://secretsatoshis.github.io/Bitcoin-Report-Library/): public Report Library data and CSV downloads.",
        "- [Source release manifest](https://secretsatoshis.github.io/Bitcoin-Report-Library/csv/release_manifest.json): report date, generation time, and file hashes for the daily data release.",
    ]
    for category in catalog["categories"]:
        lines.extend(["", f"## {category}", ""])
        for entry in catalog["charts"]:
            if entry["category"] == category:
                lines.append(
                    f"- [{entry['title']}]({CANONICAL_BASE}/{entry['url']}): {entry['description']}"
                )
    lines.extend([
        "",
        "## Related research and tools",
        "",
        "- [Secret Satoshis guide](https://secretsatoshis.com/llms.txt): the newsletter, products, public data releases, and code.",
        "- [Newsletter](https://newsletter.secretsatoshis.com/): the yearly price outlook, weekly recaps, quarterly reviews, and year-end reviews.",
        "- [Market Dashboard guide](https://dashboard.secretsatoshis.com/llms.txt): daily indicators, metric definitions, and data files.",
        "- [Agent 21 guide](https://agent21.secretsatoshis.com/llms.txt): the Bitcoin-native AI agent and its public capabilities.",
        "",
        "## Optional",
        "",
        "- [Disclaimer and licensing](https://newsletter.secretsatoshis.com/p/secret-satoshis-newsletter-disclaimer): research disclosures and terms. Code is GPL-3.0; third-party data retains its upstream terms. Nothing published here is investment advice.",
        "",
    ])
    (output_dir / "llms.txt").write_text("\n".join(lines), encoding="utf-8")


def write_catalog(output_dir, payloads):
    output_dir = Path(output_dir)
    catalog = catalog_from_payloads(payloads)
    (output_dir/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    _write_sitemap(output_dir,catalog)
    _write_robots(output_dir)
    _write_noscript_index(output_dir,catalog)
    _write_catalog_head(output_dir,catalog)
    _write_llms(output_dir, catalog)
    path=output_dir/'index.html';document=path.read_text()
    document=re.sub(r'<script id="catalog-data".*?</script>','',document,flags=re.S)
    safe=json.dumps(catalog,separators=(',',':')).replace('<','\\u003c')
    document=document.replace('placeholder="Search Bitcoin charts…"', f'placeholder="Search {catalog["chart_count"]} Bitcoin charts…"')
    document=document.replace('</body>',f'<script id="catalog-data" type="application/json">{safe}</script>\n</body>')
    path.write_text(document)
    return catalog

TAG_RULES = OrderedDict(
    [
        ("market cap", "market cap"),
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
