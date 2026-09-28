"""Decide whether a scheduled run has a new Report Library release to chart.

The chart workflow checks hourly instead of assuming the Report Library published an hour
earlier: GitHub starts scheduled jobs hours late and in no guaranteed order. A run builds
only when the published release differs from the one the committed pack was built from,
so a late or retried Report Library release is charted within the hour. Standard library
only, so the check runs before any dependency install.

Writes `build=true|false` and `release=<date>` to $GITHUB_OUTPUT when set.
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chart_definitions import REPORT_CSV_DIR  # noqa: E402


def published_release(source):
    location = f"{str(source).rstrip('/')}/release_manifest.json"
    if location.startswith(("https://", "http://")):
        # A unique query bypasses the CDN's cached copy of the manifest.
        with urlopen(f"{location}?t={time.time_ns()}", timeout=60) as response:
            manifest = json.loads(response.read())
    else:
        manifest = json.loads(Path(location).read_text())
    return manifest["report_date"]


def charted_release(pack=ROOT / "Charts"):
    try:
        return json.loads((pack / "build-manifest.json").read_text())["report_date"]
    except (OSError, ValueError, KeyError):
        return None


def main():
    published, charted = published_release(REPORT_CSV_DIR), charted_release()
    build = published != charted
    print(f"published release {published}; charted release {charted}; build={str(build).lower()}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"build={str(build).lower()}\nrelease={published}\n")


if __name__ == "__main__":
    main()
