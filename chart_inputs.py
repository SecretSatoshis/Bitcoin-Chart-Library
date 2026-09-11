"""Load a coherent, completed Report Library release before rendering charts."""
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

INPUT_FILES = (
    'master_metrics_data.csv.gz', 'drawdown_data.csv', 'cycle_low_data.csv',
    'halving_data.csv', 'report_ohlc_summary.csv',
)
RELEASE_MANIFEST_NAME = 'release_manifest.json'


def _read_bytes(path):
    if str(path).startswith(('https://', 'http://')):
        with urlopen(path, timeout=60) as response:
            return response.read()
    return Path(path).read_bytes()


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
    if len(summary) != 1 or pd.Timestamp(summary['Report Date'].iloc[0]) != date:
        raise ValueError('Summary and master must belong to the same report date')
    price = pd.to_numeric(master['price_close'], errors='coerce').iloc[-1]
    if not np.isfinite(price) or price <= 0 or not np.isclose(price, float(summary['Daily Close'].iloc[0]), rtol=1e-9):
        raise ValueError('Summary and master report-date prices disagree')
    return date


def load_chart_inputs(csv_path, now=None):
    try:
        manifest = json.loads(_read_bytes(csv_path(RELEASE_MANIFEST_NAME)))
    except (FileNotFoundError, OSError):
        # Keep existing local checkouts usable while Report Library publishes the
        # new platform manifest for the first time.
        manifest = json.loads(_read_bytes(csv_path('chart_input_manifest.json')))
        if manifest.get('version') != 1:
            raise ValueError('Missing or unsupported chart input manifest')
    else:
        if (manifest.get('schema_version') != 1
                or manifest.get('release_id') != manifest.get('report_date')):
            raise ValueError('Missing or unsupported release manifest')

    records = manifest.get('files', {})
    if not isinstance(records, dict):
        raise ValueError('Release manifest files must be an object')
    if set(INPUT_FILES) - set(records):
        raise ValueError('Release manifest is missing chart input files')
    report_date = manifest.get('report_date')
    frames = {}
    for filename in INPUT_FILES:
        payload = _read_bytes(csv_path(filename))
        expected = records[filename]
        expected_hash = expected.get('sha256') if isinstance(expected, dict) else expected
        if hashlib.sha256(payload).hexdigest() != expected_hash:
            raise ValueError(f'{filename} does not match the release manifest; retry after publication completes')
        options = {'compression': 'gzip', 'index_col': 0, 'parse_dates': True, 'low_memory': False} if filename.endswith('.gz') else {}
        frames[filename] = pd.read_csv(io.BytesIO(payload), **options)
    validate_report_dates(frames[INPUT_FILES[0]], frames['report_ohlc_summary.csv'], report_date, now)
    return frames
