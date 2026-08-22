"""
Chart-specific configuration for Bitcoin Chart Library.

All data fetching and metric calculation is handled by Bitcoin-Report-Library.
This file contains only chart-specific settings.
"""

import os

# ---------------------------------------------------------------------------
# CSV data source
# ---------------------------------------------------------------------------
# Where to find Report Library's CSV output.
#
# Supported modes:
#   GitHub URL  – "https://secretsatoshis.github.io/Bitcoin-Report-Library/csv"
#   Local path  – "../Bitcoin-Report-Library/csv"  (sibling directory layout)
#
# pandas.read_csv() accepts both local paths and URLs transparently.
#
# Default: GitHub Pages URL (works for GitHub Actions and remote usage).
# Override: set the REPORT_CSV_DIR environment variable for local development.
#   export REPORT_CSV_DIR=../Bitcoin-Report-Library/csv
# ---------------------------------------------------------------------------
REPORT_CSV_DIR = os.environ.get(
    "REPORT_CSV_DIR",
    "https://secretsatoshis.github.io/Bitcoin-Report-Library/csv",
)


def csv_path(filename):
    """Build the full path or URL for a CSV file.

    Handles both local file paths and HTTP(S) URLs so that callers
    can pass the result straight to ``pd.read_csv()`` without caring
    which mode is active.
    """
    if REPORT_CSV_DIR.startswith(("http://", "https://")):
        return f"{REPORT_CSV_DIR.rstrip('/')}/{filename}"
    return os.path.join(REPORT_CSV_DIR, filename)


def csv_source_is_remote():
    """Return True when CSVs are loaded from a URL, not a local path."""
    return REPORT_CSV_DIR.startswith(("http://", "https://"))
