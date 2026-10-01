"""Load a coherent, completed Report Library release before rendering charts."""
import hashlib
import io
import json
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

import numpy as np
import pandas as pd
from candle_inputs import CANDLE_FILES, validate_candle_inputs

INPUT_FILES = (
    'master_metrics_data.csv.gz', 'drawdown_data.csv', 'cycle_low_data.csv',
    'halving_data.csv', 'report_ohlc_summary.csv',
)
# The Report Library publishes the candle bundle in every release. A release without it
# is broken, not a line-only release, so it is required like every other input.
REQUIRED_FILES = (*INPUT_FILES, *CANDLE_FILES)
RELEASE_MANIFEST_NAME = 'release_manifest.json'

# GitHub Pages serves every file with a 10-minute CDN cache. Remote reads key each file
# to its release (and the manifest to the request time) so a cached copy of an older
# release cannot be mixed in, and retry briefly while a new deployment propagates.
REMOTE_ATTEMPTS = 3
REMOTE_RETRY_SECONDS = 20

READ_OPTIONS = {
    'master_metrics_data.csv.gz': {'compression': 'gzip', 'index_col': 0, 'parse_dates': True, 'low_memory': False},
    'weekly_metrics_data.csv.gz': {'compression': 'gzip', 'index_col': 0, 'parse_dates': True, 'low_memory': False},
    'monthly_metrics_data.csv.gz': {'compression': 'gzip', 'index_col': 0, 'parse_dates': True, 'low_memory': False},
    'bitcoin_candles.csv.gz': {'compression': 'gzip'},
}


def _is_remote(path):
    return str(path).startswith(('https://', 'http://'))


def _read_bytes(path, query=None):
    if _is_remote(path):
        url = f'{path}?{query}' if query else str(path)
        with urlopen(url, timeout=60) as response:
            return response.read()
    return Path(path).read_bytes()


def _read_verified(path, filename, expected_hash, release_id):
    """Read one input and require its manifest hash, retrying remote CDN propagation."""
    remote = _is_remote(path)
    for attempt in range(1, (REMOTE_ATTEMPTS if remote else 1) + 1):
        payload = _read_bytes(path, f'release={quote(str(release_id))}' if remote else None)
        if hashlib.sha256(payload).hexdigest() == expected_hash:
            return payload
        if attempt < REMOTE_ATTEMPTS and remote:
            time.sleep(REMOTE_RETRY_SECONDS)
    raise ValueError(f'{filename} does not match the release manifest; retry after publication completes')


def validate_report_dates(master, summary, report_date, now=None, max_age_days=2):
    date = pd.Timestamp(report_date)
    today = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    today = today.tz_convert('UTC').tz_localize(None) if today.tz is not None else today
    today = today.normalize()
    if pd.isna(date) or date.tz is not None or date != date.normalize():
        raise ValueError('Release report date must be a valid UTC calendar date')
    age = (today - date).days
    if age < 1 or age > max_age_days:
        raise ValueError(f'Release date {date.date()} is not a recent completed UTC day')
    index = master.index
    if (not isinstance(index, pd.DatetimeIndex) or index.empty or index.hasnans
            or index.tz is not None or index.has_duplicates
            or not index.is_monotonic_increasing
            or not index.equals(pd.date_range(index[0], date, freq='D'))):
        raise ValueError('Master calendar must be complete, unique and end on the release date')
    if len(summary) != 1 or pd.Timestamp(summary['date'].iloc[0]) != date:
        raise ValueError('Summary and master must belong to the same report date')
    price = pd.to_numeric(master['price_close'], errors='coerce').iloc[-1]
    if not np.isfinite(price) or price <= 0 or not np.isclose(price, float(summary['daily_close'].iloc[0]), rtol=1e-9):
        raise ValueError('Summary and master report-date prices disagree')
    return date


def load_chart_inputs(csv_path, now=None, *, frozen_report_date=None):
    manifest = json.loads(_read_bytes(csv_path(RELEASE_MANIFEST_NAME), f't={time.time_ns()}'))
    if (manifest.get('schema_version') != 1
            or manifest.get('release_id') != manifest.get('report_date')):
        raise ValueError('Missing or unsupported release manifest')

    records = manifest.get('files', {})
    if not isinstance(records, dict):
        raise ValueError('Release manifest files must be an object')
    missing = set(REQUIRED_FILES) - set(records)
    if missing:
        raise ValueError(f'Release manifest is missing chart input files: {sorted(missing)}')
    report_date = manifest.get('report_date')
    frames = {}
    for filename in REQUIRED_FILES:
        payload = _read_verified(csv_path(filename), filename, records[filename]['sha256'], manifest.get('release_id'))
        frames[filename] = pd.read_csv(io.BytesIO(payload), **READ_OPTIONS.get(filename, {}))
    validation_now = now
    if frozen_report_date is not None:
        if report_date != frozen_report_date:
            raise ValueError('Frozen release report date does not match requested cutoff')
        today = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
        today = today.tz_convert('UTC').tz_localize(None) if today.tz is not None else today
        date = pd.Timestamp(report_date)
        if date.tz is not None or date >= today.normalize():
            raise ValueError('Frozen release must describe a completed UTC day')
        # Explicit historical exports retain all integrity checks, with freshness
        # relative to the requested release instead of the wall clock.
        validation_now = date + pd.Timedelta(days=1)
    validate_report_dates(frames[INPUT_FILES[0]], frames['report_ohlc_summary.csv'], report_date, validation_now)
    validate_candle_inputs(frames, report_date)
    frames[INPUT_FILES[0]].attrs['release_manifest'] = manifest
    return frames
