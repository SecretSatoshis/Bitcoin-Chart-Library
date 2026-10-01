"""Decide whether the live chart site needs a rebuild for a new Report Library release.

GitHub starts scheduled jobs late and in no guaranteed order, so the workflow checks
hourly rather than at a fixed time after the Report Library. It rebuilds when the
published release differs from the one the live site was built from; a failed build is
therefore retried within the hour. Standard library only, so it runs without an install.

Writes `build=true|false` and `release=<date>` to $GITHUB_OUTPUT when set.
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chart_catalog import CANONICAL_BASE  # noqa: E402
from chart_definitions import REPORT_CSV_DIR  # noqa: E402


def report_date(source, filename):
    """`report_date` from a JSON manifest at a URL or local folder, or None if it is absent."""
    location = f"{str(source).rstrip('/')}/{filename}"
    try:
        if location.startswith(("https://", "http://")):
            # A unique query bypasses any cached copy.
            with urlopen(f"{location}?t={time.time_ns()}", timeout=60) as response:
                return json.loads(response.read())["report_date"]
        return json.loads(Path(location).read_text())["report_date"]
    except HTTPError as error:
        if error.code == 404:
            return None
        raise
    except FileNotFoundError:
        return None


def main():
    published = report_date(REPORT_CSV_DIR, "release_manifest.json")
    if published is None:
        raise SystemExit("The Report Library has no published release manifest")
    live = report_date(CANONICAL_BASE, "build-manifest.json")
    build = published != live
    print(f"published release {published}; live charts {live}; build={str(build).lower()}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"build={str(build).lower()}\nrelease={published}\n")


if __name__ == "__main__":
    main()
