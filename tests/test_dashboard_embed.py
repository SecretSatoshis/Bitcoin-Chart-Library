"""The Report Library vendors three self-contained frames from the canonical renderer."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_sync_vendors_three_frames_and_verified_runtime(tmp_path):
    output = tmp_path / "dashboard/static/shared-chart"
    subprocess.run([sys.executable, str(ROOT / "scripts/sync-dashboard.py"), str(output)], check=True)
    manifest = json.loads((output / "source-manifest.json").read_text())
    assert manifest["frames"] == ["frame.html", "seasonal-mtd.html", "seasonal-ytd.html"]
    for name, digest in manifest["vendored_hashes"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    for filename, chart_id in zip(manifest["frames"], ["dashboard-price-outlook", "dashboard-seasonal-mtd", "dashboard-seasonal-ytd"]):
        html = (output / filename).read_text()
        assert f'data-chart-id="{chart_id}"' in html
        assert "@@" not in html
        for asset in re.findall(r'(?:src|href)="(assets/[^\"]+|embed-host.js)"', html):
            assert (output / asset).is_file()
        assert 'id="chart-data"' in html
    for license_name in ("LICENSE", "NOTICE", "JetBrainsMono-OFL.txt", "Syne-OFL.txt"):
        assert (output / "assets" / license_name).is_file()
    assert manifest["files"]["renderer.js"] == hashlib.sha256((ROOT / "web/renderer.js").read_bytes()).hexdigest()


def test_dashboard_price_series_colors_are_distinct(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts/sync-dashboard.py"),
                    str(tmp_path / "dashboard/static/shared-chart")], check=True)
    colors = json.loads((tmp_path / "dashboard/components/chart-colors.json").read_text())
    assert len(colors) == 7 and len(set(colors.values())) == 7, colors
