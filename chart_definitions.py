"""
Chart-specific configuration for Bitcoin Chart Library.

All data fetching and metric calculation is handled by Bitcoin-Report-Library.
This file contains only chart-specific settings.
"""

import os

# ---------------------------------------------------------------------------
# CSV data source
# ---------------------------------------------------------------------------
# Where to find Report Library's CSV release (the default for `main.py --csv-dir`).
#
# Supported modes:
#   GitHub URL  – "https://secretsatoshis.github.io/Bitcoin-Report-Library/csv"
#   Local path  – "../Bitcoin-Report-Library/csv"  (sibling directory layout)
#
# chart_inputs.py reads release_manifest.json from this location, then fetches each
# input and verifies its SHA-256 against the manifest before anything is rendered.
#
# Default: GitHub Pages URL (works for GitHub Actions and remote usage).
# Override: set the REPORT_CSV_DIR environment variable for local development.
#   export REPORT_CSV_DIR=../Bitcoin-Report-Library/csv
# ---------------------------------------------------------------------------
REPORT_CSV_DIR = os.environ.get(
    "REPORT_CSV_DIR",
    "https://secretsatoshis.github.io/Bitcoin-Report-Library/csv",
)
