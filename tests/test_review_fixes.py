"""Release integrity, cycle scaling, missing observations and runtime regressions."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from chart_inputs import INPUT_FILES, load_chart_inputs, validate_report_dates


def _release(tmp_path):
    master = pd.DataFrame({'price_close': [100., 80., 120.]},
                          index=pd.date_range('2026-09-06', periods=3, name='time'))
    master.to_csv(tmp_path / INPUT_FILES[0])
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
            for name in INPUT_FILES
        },
    }
    (tmp_path/'release_manifest.json').write_text(json.dumps(manifest))
    return master, summary


def test_manifest_loads_matching_release(tmp_path):
    _release(tmp_path)
    frames = load_chart_inputs(lambda name: tmp_path/name, now='2026-09-09')
    assert len(frames) == 5
    assert frames[INPUT_FILES[0]].price_close.iloc[-1] == 120


def test_legacy_manifest_is_not_accepted(tmp_path):
    _release(tmp_path)
    (tmp_path / 'release_manifest.json').unlink()
    (tmp_path / 'chart_input_manifest.json').write_text('{}')
    with pytest.raises(FileNotFoundError):
        load_chart_inputs(lambda name: tmp_path / name, now='2026-09-09')


@pytest.mark.parametrize('filename', INPUT_FILES)
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
