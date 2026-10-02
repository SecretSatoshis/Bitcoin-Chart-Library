"""Auto-discovered chart definitions: no separate website registration required."""
import copy
import importlib
import pkgutil
import re
import math

CATEGORY_ORDER = ['Price & Trends', 'Returns & Comparisons', 'Bitcoin ETFs', 'Cycles & Seasonality',
                  'Valuation Models', 'Relative Valuation', 'Holder Sentiment',
                  'Supply', 'Network Activity', 'Mining & Security']
UNITS = {'USD', 'percent', 'ratio', 'BTC', 'BTC/day', 'count', 'hashrate', 'sats/USD', 'USD/TH/s/day'}


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
        if chart['family'] not in ('timeseries', 'cycle', 'seasonal', 'etf'):
            raise ValueError(f'{name}: unsupported family')
        if chart.get('default_presentation', 'line') not in ('line', 'candles'):
            raise ValueError(f'{name}: invalid default presentation')
        if chart.get('default_interval', 'daily') not in ('daily', 'weekly', 'monthly'):
            raise ValueError(f'{name}: invalid default candle interval')
        if not chart.get('axes') or set(chart['axes']) - {'right', 'left'}:
            raise ValueError(f'{name}: invalid axes')
        metrics = {s.get('data'): s.get('axis', 'right') for s in chart.get('y_data', [])}
        for axis_id, axis in chart['axes'].items():
            if axis['unit'] not in UNITS or axis['mode'] not in ('linear', 'log'):
                raise ValueError(f'{name}: invalid axis unit/mode')
            if 'reference_lines' in axis:
                lines = axis['reference_lines']
                if not isinstance(lines, list) or any(
                    not isinstance(line, dict)
                    or type(line.get('value')) not in (int, float)
                    or not math.isfinite(line['value'])
                    or not isinstance(line.get('label'), str) or not line['label'].strip()
                    for line in lines
                ):
                    raise ValueError(f'{name}: invalid axis reference lines')
            if 'value_bands' in axis:
                if any(key in axis and type(axis[key]) is not bool for key in ('band_labels', 'band_fill')):
                    raise ValueError(f'{name}: invalid band visibility option')
                bands = axis['value_bands']
                if not isinstance(bands, list) or not bands:
                    raise ValueError(f'{name}: value bands must be a nonempty list')
                for band in bands:
                    if not isinstance(band, dict) or any(
                        not isinstance(band.get(k), str) or not band[k].strip()
                        for k in ('label', 'color')
                    ):
                        raise ValueError(f'{name}: invalid value band label/color')
                    for edge in ('lower', 'upper'):
                        value = band[edge]
                        if value is not None and not (
                            type(value) in (int, float) and math.isfinite(value)
                            or isinstance(value, str) and metrics.get(value) == axis_id
                        ):
                            raise ValueError(f'{name}: invalid value band boundary')
                if axis.get('band_anchor') is not None and metrics.get(axis['band_anchor']) != axis_id:
                    raise ValueError(f'{name}: invalid band anchor')
                bounds = axis.get('band_range')
                if bounds is not None and (not isinstance(bounds, list) or len(bounds) != 2
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds)
                    or bounds[0] >= bounds[1]):
                    raise ValueError(f'{name}: invalid band display range')
        if 'ranges' in chart and chart.get('default_range') not in chart['ranges']:
            raise ValueError(f'{name}: default range is not one of its ranges')
        if chart.get('flow_intervals') and chart.get('default_flow_interval') not in chart['flow_intervals']:
            raise ValueError(f'{name}: default flow frequency is not one of its frequencies')
        for series in chart.get('y_data', []):
            if series.get('axis', 'right') not in chart['axes']:
                raise ValueError(f'{name}: series has no matching axis')
            if series.get('line_style', 'solid') not in ('solid', 'dashed'):
                raise ValueError(f'{name}: invalid line style')
        if 'panels' in chart:
            panels = chart['panels']
            if not isinstance(panels, list) or not panels:
                raise ValueError(f'{name}: panels must be a nonempty list')
            if any(not isinstance(panel, dict) or panel.get('axis') not in chart['axes']
                   for panel in panels):
                raise ValueError(f'{name}: every panel must reference an existing axis')
            assigned = [panel['axis'] for panel in panels]
            if len(set(assigned)) != len(assigned) or set(assigned) != set(chart['axes']):
                raise ValueError(f'{name}: panels must assign each axis exactly once')
            for panel in panels:
                if any(not isinstance(panel.get(key), str) or not panel[key].strip()
                       for key in ('label', 'control_label')):
                    raise ValueError(f'{name}: panel labels are required')
                weight = panel.get('weight')
                if type(weight) not in (int, float) or not math.isfinite(weight) or weight <= 0:
                    raise ValueError(f'{name}: panel weights must be positive and finite')
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
