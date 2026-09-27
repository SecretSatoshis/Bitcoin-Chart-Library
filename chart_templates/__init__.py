"""Auto-discovered chart definitions: no separate website registration required."""
import copy
import importlib
import pkgutil
import re

CATEGORY_ORDER = ['Price Models', 'On-chain Valuation', 'Asset Comparisons',
                  'Relative Valuation', 'Cycle Analysis', 'Returns and Performance',
                  'Supply', 'Network Activity', 'Mining and Security', 'Holder Behavior']
UNITS = {'USD', 'percent', 'ratio', 'BTC', 'BTC/day', 'BTC-days', 'count', 'hashrate', 'sats/USD', 'USD/TH/s/day'}


def validate_templates(templates):
    seen = set()
    for chart in templates:
        name = chart['filename']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in seen or name == 'index':
            raise ValueError(f'Invalid or duplicate chart filename: {name}')
        seen.add(name)
        for field in ('title', 'description', 'category', 'data_source'):
            if not isinstance(chart.get(field), str) or not chart[field].strip():
                raise ValueError(f'{name}: missing {field}')
        if chart['family'] not in ('timeseries', 'cycle', 'seasonal'):
            raise ValueError(f'{name}: unsupported family')
        if not chart.get('axes') or set(chart['axes']) - {'right', 'left'}:
            raise ValueError(f'{name}: invalid axes')
        for axis in chart['axes'].values():
            if axis['unit'] not in UNITS or axis['mode'] not in ('linear', 'log'):
                raise ValueError(f'{name}: invalid axis unit/mode')
        for series in chart.get('y_data', []):
            if series.get('axis', 'right') not in chart['axes']:
                raise ValueError(f'{name}: series has no matching axis')
    if not seen:
        raise ValueError('No templates discovered')
    return templates


def load_templates():
    charts = []
    for module in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if not module.name.startswith('_'):
            charts.extend(copy.deepcopy(getattr(importlib.import_module(f'{__name__}.{module.name}'), 'CHARTS', [])))
    return validate_templates(charts)


def get_template(filename):
    return next(chart for chart in load_templates() if chart['filename'] == filename)
