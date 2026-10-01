"""Where the charts read the Report Library release from."""

import os

# The published release on GitHub Pages, or a local release folder for development:
#   REPORT_CSV_DIR=../Bitcoin-Report-Library/csv
# `main.py --csv-dir` overrides both. chart_inputs.py checks every file against the
# release manifest before anything is built.
REPORT_CSV_DIR = os.environ.get(
    "REPORT_CSV_DIR",
    "https://secretsatoshis.github.io/Bitcoin-Report-Library/csv",
)
