import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    # Several tests check the built site, so a missing build should say so plainly.
    if not (PROJECT_ROOT / "Charts" / "catalog.json").is_file():
        raise pytest.UsageError("Build the charts first: uv run --no-sync python main.py")
