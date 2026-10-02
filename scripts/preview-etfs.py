"""Build only the ETF charts for local review; leave the production chart pack alone."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chart_build import build_pack
from chart_templates.etfs import CHARTS

# Catalog text replaced so the preview can't be mistaken for the public site.
REPLACEMENTS = [
    ('<title>Bitcoin Chart Library |', '<title>Bitcoin ETF Charts |'),
    ('Bitcoin Chart Library<span', 'Bitcoin ETF Charts<span'),
    ('//</span> Chart Library', '//</span> Local chart review'),
    ('Explore interactive charts of Bitcoin’s price, valuation, on-chain activity, and market cycles.',
     'Explore ETF flows, holdings, assets, and entry prices. Built from our Report Library data.'),
    ('See how the charts are built and which data they use.', 'Local preview of the ETF charts.'),
    ('name="robots" content="index, follow, max-image-preview:large"', 'name="robots" content="noindex"'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv-dir', default=str(ROOT.parent / 'Bitcoin-Report-Library' / 'csv'))
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs' / 'etf-preview')
    args = parser.parse_args()
    result = build_pack(args.csv_dir, args.output, templates=CHARTS)
    path = args.output / 'index.html'
    page = path.read_text()
    for old, new in REPLACEMENTS:
        if old not in page:
            raise ValueError(f'Catalog page no longer contains {old!r}; update the preview text')
        page = page.replace(old, new)
    path.write_text(page)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
