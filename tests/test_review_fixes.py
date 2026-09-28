"""Release integrity, cycle scaling, missing observations and runtime regressions."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import chart_inputs
from candle_inputs import CANDLE_FILES
from chart_inputs import INPUT_FILES, REQUIRED_FILES, load_chart_inputs, validate_report_dates


def _candle_bundle(master):
    """Daily/weekly/monthly candles and period snapshots shaped like the Report Library's."""
    rows = []
    for interval, frequency in (('daily', 'D'), ('weekly', 'W-SUN'), ('monthly', 'M')):
        for period, prices in master.price_close.groupby(master.index.to_period(frequency)):
            start, end = period.start_time.normalize(), period.end_time.normalize()
            if prices.index[0] != start:
                continue
            rows.append({'interval': interval, 'period_start': start, 'period_end': end,
                         'observation_date': prices.index[-1], 'complete': prices.index[-1] == end,
                         'Open': prices.iloc[0], 'High': prices.max(), 'Low': prices.min(),
                         'Close': prices.iloc[-1]})
    candles = pd.DataFrame(rows)
    snapshots = {}
    for interval, filename in (('weekly', CANDLE_FILES[1]), ('monthly', CANDLE_FILES[2])):
        chosen = candles.loc[candles.interval.eq(interval)]
        snapshot = master.reindex(pd.DatetimeIndex(chosen.observation_date)).copy()
        snapshot.index = pd.DatetimeIndex(chosen.period_start, name='time')
        snapshots[filename] = snapshot
    return candles, snapshots


def _release(tmp_path):
    master = pd.DataFrame({'price_close': [100., 80., 120., 110., 90., 105., 115., 120.]},
                          index=pd.date_range('2026-09-01', periods=8, name='time'))
    master.to_csv(tmp_path / INPUT_FILES[0])
    candles, snapshots = _candle_bundle(master)
    candles.to_csv(tmp_path / CANDLE_FILES[0], index=False, compression='gzip', date_format='%Y-%m-%d')
    for filename, snapshot in snapshots.items():
        snapshot.to_csv(tmp_path / filename, compression='gzip', date_format='%Y-%m-%d')
    for name in INPUT_FILES[1:4]:
        pd.DataFrame({'test': [1]}).to_csv(tmp_path / name, index=False)
    summary = pd.DataFrame({'Report Date': ['2026-09-08'], 'Daily Close': [120.]})
    summary.to_csv(tmp_path / INPUT_FILES[-1], index=False)
    manifest = {
        'schema_version': 1,
        'release_id': '2026-09-08',
        'report_date': '2026-09-08',
        'generated_at': '2026-09-09T00:00:00+00:00',
        'files': {
            name: {
                'sha256': hashlib.sha256((tmp_path / name).read_bytes()).hexdigest(),
                'size_bytes': (tmp_path / name).stat().st_size,
            }
            for name in REQUIRED_FILES
        },
    }
    (tmp_path/'release_manifest.json').write_text(json.dumps(manifest))
    return master, summary


def test_manifest_loads_matching_release(tmp_path):
    _release(tmp_path)
    frames = load_chart_inputs(lambda name: tmp_path/name, now='2026-09-09')
    assert len(frames) == len(REQUIRED_FILES) == 8
    assert frames[INPUT_FILES[0]].price_close.iloc[-1] == 120


def test_release_without_the_candle_bundle_is_rejected(tmp_path):
    _release(tmp_path)
    manifest = json.loads((tmp_path / 'release_manifest.json').read_text())
    for name in CANDLE_FILES:
        del manifest['files'][name]
    (tmp_path / 'release_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='missing chart input files'):
        load_chart_inputs(lambda name: tmp_path / name, now='2026-09-09')


def test_remote_reads_are_release_keyed_and_retry_stale_copies(tmp_path, monkeypatch):
    _release(tmp_path)
    base = 'https://example.test/csv'
    requested, served_stale = [], set()

    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *exc): return False
        def read(self): return self.payload

    def fake_urlopen(url, timeout):
        requested.append(url)
        name = url[len(base) + 1:].split('?')[0]
        payload = (tmp_path / name).read_bytes()
        # The first read of the master is a stale CDN copy from an older release.
        if name == INPUT_FILES[0] and name not in served_stale:
            served_stale.add(name)
            payload += b'stale'
        return Response(payload)

    monkeypatch.setattr(chart_inputs, 'urlopen', fake_urlopen)
    monkeypatch.setattr(chart_inputs.time, 'sleep', lambda seconds: None)
    frames = load_chart_inputs(lambda name: f'{base}/{name}', now='2026-09-09')
    assert frames[INPUT_FILES[0]].price_close.iloc[-1] == 120
    assert requested[0].startswith(f'{base}/release_manifest.json?t=')
    assert all(url.endswith('?release=2026-09-08') for url in requested[1:])
    assert sum(INPUT_FILES[0] in url for url in requested) == 2


def test_legacy_manifest_is_not_accepted(tmp_path):
    _release(tmp_path)
    (tmp_path / 'release_manifest.json').unlink()
    (tmp_path / 'chart_input_manifest.json').write_text('{}')
    with pytest.raises(FileNotFoundError):
        load_chart_inputs(lambda name: tmp_path / name, now='2026-09-09')


@pytest.mark.parametrize('filename', REQUIRED_FILES)
def test_manifest_rejects_one_changed_input(tmp_path, filename):
    _release(tmp_path)
    with (tmp_path/filename).open('ab') as handle:
        handle.write(b'\n')
    with pytest.raises(ValueError, match='does not match'):
        load_chart_inputs(lambda name: tmp_path/name, now='2026-09-09')


@pytest.mark.parametrize('date', ['2026-09-07', '2026-09-09', '2026-10-09'])
def test_release_date_must_match_and_be_completed(tmp_path, date):
    master, summary = _release(tmp_path)
    with pytest.raises(ValueError):
        validate_report_dates(master, summary, date, now='2026-09-09')


def test_release_rejects_missing_or_duplicate_day(tmp_path):
    master, summary = _release(tmp_path)
    for broken in [master.drop(master.index[1]), pd.concat([master, master.iloc[-1:]])]:
        with pytest.raises(ValueError, match='calendar'):
            validate_report_dates(broken, summary, '2026-09-08', now='2026-09-09')


def test_frozen_export_retains_integrity_without_requiring_current_release(tmp_path):
    _release(tmp_path)
    frames=load_chart_inputs(lambda name:tmp_path/name,now='2026-12-01',frozen_report_date='2026-09-08')
    assert frames[INPUT_FILES[0]].index[-1]==pd.Timestamp('2026-09-08')
    with pytest.raises(ValueError,match='cutoff'):
        load_chart_inputs(lambda name:tmp_path/name,now='2026-12-01',frozen_report_date='2026-09-09')
    with pytest.raises(ValueError,match='completed'):
        load_chart_inputs(lambda name:tmp_path/name,now='2026-09-08',frozen_report_date='2026-09-08')
    with (tmp_path/INPUT_FILES[0]).open('ab') as handle:handle.write(b'changed')
    with pytest.raises(ValueError,match='manifest'):
        load_chart_inputs(lambda name:tmp_path/name,now='2026-12-01',frozen_report_date='2026-09-08')


def test_frozen_export_refuses_the_published_pack(tmp_path):
    from chart_build import ROOT, build_single
    with pytest.raises(ValueError, match='published Charts'):
        build_single(tmp_path, 'Bitcoin_Price', ROOT / 'Charts' / 'frozen.html',
                     frozen_report_date='2026-09-08')


def test_release_status_builds_only_for_a_new_release(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location('release_status', Path(__file__).parents[1] / 'scripts/release-status.py')
    status = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(status)
    (tmp_path / 'release_manifest.json').write_text(json.dumps({'report_date': '2026-09-08'}))
    assert status.published_release(tmp_path) == '2026-09-08'
    pack = tmp_path / 'pack'
    assert status.charted_release(pack) is None
    pack.mkdir()
    (pack / 'build-manifest.json').write_text(json.dumps({'report_date': '2026-09-08'}))
    assert status.charted_release(pack) == '2026-09-08'
