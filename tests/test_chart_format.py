import numpy as np
import pandas as pd
import pytest

import chart_format as charts


def _disable_writes(monkeypatch):
    monkeypatch.setattr(charts, "save_chart_html", lambda fig, filename: None)


def _trace(figure, name):
    return next(trace for trace in figure.data if trace.name == str(name))


def test_base_layout_is_responsive_and_branding_is_self_contained():
    assert "width" not in charts.BASE_CHART_LAYOUT
    assert charts.BASE_CHART_LAYOUT["margin"]["r"] > 0
    assert charts.BASE_CHART_LAYOUT["margin"]["b"] > 0
    assert charts.BRANDING_CONFIG["logo_url"].startswith("data:image/png;base64,")


def test_macro_supply_preserves_report_library_compatibility_labels():
    series = {
        item["data"]: item["name"] for item in charts.macro_supply["y_data"]
    }
    assert series["liquid_supply"] == "Liquid Supply"
    assert series["illiquid_supply"] == "Illiquid Supply"


def test_monthly_returns_preserve_missing_calendar_days(monkeypatch):
    _disable_writes(monkeypatch)
    # Fixed dates: the reporting period is derived from the data, not the clock, so the
    # test no longer needs to know what day it is.
    dates = pd.to_datetime(
        [
            "2024-07-31",  # baseline for August 2024
            "2024-08-01",
            "2024-08-03",
            "2025-07-31",  # baseline for August 2025
            "2025-08-01",
            "2025-08-03",
        ]
    )
    data = pd.DataFrame(
        {"price_close": [100, 110, 130, 200, 220, 260]}, index=dates
    )

    figure = charts.create_monthly_returns(data)
    current_trace = _trace(figure, 2025)

    assert np.isnan(current_trace.y[1])
    assert pd.Timestamp(current_trace.x[2]).day == 3
    # Measured from the 2025-07-31 close of 200, not August's own first observation.
    assert current_trace.y[2] == pytest.approx(30.0)


def test_monthly_returns_measure_from_the_close_before_the_month(monkeypatch):
    """C1 — the first day's move must survive; indexing off Aug 1 would erase it."""
    _disable_writes(monkeypatch)
    dates = pd.to_datetime(["2025-07-31", "2025-08-01", "2025-08-02"])
    data = pd.DataFrame({"price_close": [100.0, 110.0, 121.0]}, index=dates)

    figure = charts.create_monthly_returns(data)
    trace = _trace(figure, 2025)

    assert trace.y[0] == pytest.approx(10.0)
    assert trace.y[1] == pytest.approx(21.0)


def test_indexed_monthly_returns_reject_missing_current_month(monkeypatch):
    _disable_writes(monkeypatch)
    data = pd.DataFrame(
        {"price_close": [100, 110]},
        index=pd.to_datetime(["2025-08-01", "2025-08-02"]),
    )

    with pytest.raises(ValueError, match="refusing to leave an older indexed MTD chart"):
        charts.create_indexed_monthly_returns(data)


def test_yearly_returns_preserve_missing_calendar_days(monkeypatch):
    _disable_writes(monkeypatch)
    data = pd.DataFrame(
        {"price_close": [100, 100, 130]},
        index=pd.to_datetime(["2024-12-31", "2025-01-01", "2025-01-03"]),
    )

    figure = charts.create_yearly_returns(data)
    current_trace = _trace(figure, 2025)

    assert np.isnan(current_trace.y[1])
    third_date = pd.Timestamp(current_trace.x[2])
    assert third_date.month == 1 and third_date.day == 3
    # Measured from the 2024-12-31 close of 100.
    assert current_trace.y[2] == pytest.approx(30.0)


def test_yearly_returns_measure_from_the_prior_year_close(monkeypatch):
    """C1 — January 1's own move is part of YTD, so the baseline is December 31."""
    _disable_writes(monkeypatch)
    data = pd.DataFrame(
        {"price_close": [100.0, 120.0]},
        index=pd.to_datetime(["2024-12-31", "2025-01-01"]),
    )

    figure = charts.create_yearly_returns(data)
    trace = _trace(figure, 2025)

    assert trace.y[0] == pytest.approx(20.0)


def test_indexed_yearly_returns_reject_missing_baseline(monkeypatch):
    """The reporting year now comes from the data, so the reachable failure is a
    missing baseline: nothing to index the year against."""
    _disable_writes(monkeypatch)
    data = pd.DataFrame(
        {"price_close": [100, 110]},
        index=pd.to_datetime(["2025-01-01", "2025-01-02"]),
    )

    with pytest.raises(
        ValueError, match="refusing to leave an older indexed YTD chart in place"
    ):
        charts.create_indexed_yearly_returns(data)


def test_indexed_yearly_returns_skip_partial_historical_year(monkeypatch):
    _disable_writes(monkeypatch)
    prior_dates = pd.date_range("2024-01-01", "2024-01-31")
    current_dates = pd.to_datetime(["2025-01-01", "2025-01-02"])
    dates = prior_dates.append(current_dates)
    data = pd.DataFrame({"price_close": np.arange(1, len(dates) + 1)}, index=dates)

    figure = charts.create_indexed_yearly_returns(data)

    assert "2024" not in {trace.name for trace in figure.data}
    assert "2025" in {trace.name for trace in figure.data}


def test_indexed_yearly_reference_dates_exclude_leap_day(monkeypatch):
    _disable_writes(monkeypatch)
    data = pd.DataFrame(
        {"price_close": [90, 100, 120]},
        index=pd.to_datetime(["2023-12-31", "2024-01-01", "2024-03-01"]),
    )

    figure = charts.create_indexed_yearly_returns(data)
    current_trace = _trace(figure, 2024)
    dates = pd.DatetimeIndex(current_trace.x)

    assert len(dates) == 365
    assert not ((dates.month == 2) & (dates.day == 29)).any()
    assert dates[-1] == pd.Timestamp("2024-12-31")
    march_1 = dates.get_loc(pd.Timestamp("2024-03-01"))
    assert current_trace.y[march_1] == pytest.approx(120.0)


def test_single_axis_templates_use_the_primary_axis():
    for template in (charts.chart_transactions, charts.chart_hashrate):
        assert {series["yaxis"] for series in template["y_data"]} == {"y"}
        assert template["y1_label"]
        assert template["y2_label"] == ""

    assert charts.chart_thermocap_multiple["y2_label"] == ""
    assert charts.chart_price_ma["filter_start_date"] == "2011-01-01"


def test_optional_metric_does_not_abort_chart_generation():
    template = {
        "y_data": [
            {"name": "Price", "data": "price_close", "yaxis": "y"},
            {"name": "Optional", "data": "not_available", "yaxis": "y", "optional": True},
        ],
        "title": "Optional metric",
        "x_label": "Date",
        "y1_label": "Price",
        "y2_label": "",
        "filename": "optional_metric",
        "data_source": "Local test",
    }
    data = pd.DataFrame(
        {"price_close": [1, 2]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"])
    )

    with pytest.warns(RuntimeWarning, match="Skipping optional metric"):
        figure = charts.create_line_chart(template, data)

    assert [trace.name for trace in figure.data] == ["Price"]


def test_date_axis_title_is_suppressed():
    template = {
        "y_data": [{"name": "Price", "data": "price_close", "yaxis": "y"}],
        "title": "Date axis title",
        "x_label": "Date",
        "y1_label": "Price",
        "y2_label": "",
        "filename": "date_axis_title",
        "data_source": "Local test",
    }
    data = pd.DataFrame(
        {"price_close": [1, 2]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"])
    )

    figure = charts.create_line_chart(template, data)

    assert figure.layout.xaxis.title.text is None


def test_new_model_templates_and_commodity_ticker_are_registered():
    new_templates = {
        "Bitcoin_Electricity_Cost": {
            "Electricity_Cost_3c",
            "Electricity_Cost_4c",
            "Electricity_Cost_5c",
            "Electricity_Cost_6c",
            "Electricity_Cost_7c",
        },
        "Bitcoin_Power_Law_Model": {
            "power_law_price",
            "power_law_price_multiple",
        },
        "Bitcoin_Metcalfe_Model": {
            "metcalfe_value_any_balance",
            "metcalfe_value_0p001_btc",
            "metcalfe_value_0p01_btc",
            "metcalfe_value_0p1_btc",
            "metcalfe_price_multiple",
        },
        "Bitcoin_Hash_Ribbons": {
            "30_day_ma_hash_rate",
            "60_day_ma_hash_rate",
        },
    }
    templates_by_filename = {
        template["filename"]: template for template in charts.chart_templates
    }

    for filename, expected_metrics in new_templates.items():
        assert filename in templates_by_filename
        actual_metrics = {
            series["data"] for series in templates_by_filename[filename]["y_data"]
        }
        assert {"price_close", *expected_metrics}.issubset(actual_metrics)

    full_ytd_metrics = {
        series["data"] for series in charts.ytd_return_full["y_data"]
    }
    assert "^SPGSCI_close_YTD_change" in full_ytd_metrics
    assert "^BCOM_close_YTD_change" not in full_ytd_metrics


def test_relative_value_sector_templates_and_equities_cover_stock_catalog():
    templates_by_filename = {
        template["filename"]: template for template in charts.chart_templates
    }
    expected_groups = {
        "Bitcoin_RV_Semiconductors": {"NVDA", "AVGO", "TSM", "005930.KS", "MU"},
        "Bitcoin_RV_Financials": {"BRK-B", "JPM", "GS", "V", "PYPL", "XYZ"},
        "Bitcoin_RV_Sector_Leaders": {"TSLA", "LLY", "2222.SR", "SPCX"},
    }

    for filename, tickers in expected_groups.items():
        template = templates_by_filename[filename]
        expected_fields = {
            charts.EQUITY_RELATIVE_VALUE_SERIES[ticker][1] for ticker in tickers
        }
        actual_fields = {series["data"] for series in template["y_data"]}
        assert {"price_close", *expected_fields}.issubset(actual_fields)
        assert template["filter_start_date"] == "2015-01-01"

    equity_fields = {series["data"] for series in charts.chart_equities["y_data"]}
    expected_equity_fields = {
        field for _, field in charts.EQUITY_RELATIVE_VALUE_SERIES.values()
    }
    assert equity_fields == {"price_close", *expected_equity_fields}
    assert charts.chart_equities["legend_yanchor"] == "top"
    assert charts.chart_equities["bottom_margin"] > charts.BASE_CHART_LAYOUT["margin"]["b"]


def test_selected_recent_bitcoin_industry_events_are_annotated():
    events_by_name = {event["name"]: event for event in charts.BITCOIN_HISTORICAL_EVENTS}

    reserve = events_by_name["U.S. Strategic Bitcoin Reserve"]
    strategy_sale = events_by_name["Strategy Sells Bitcoin"]

    assert reserve["dates"] == ["2025-03-06"]
    assert strategy_sale["dates"] == ["2026-06-29"]
    assert "annotation_y" not in reserve
    assert "annotation_y" not in strategy_sale
    assert "Bitcoin ETF Options" not in events_by_name
    assert "SAB 121 Rescinded" not in events_by_name
    assert "In-Kind ETF Approval" not in events_by_name


def test_report_period_comes_from_the_data_not_the_clock():
    """M4 — a run near a period boundary must describe the data it was given."""
    prices = charts._positive_price_series(
        pd.Series(
            [100.0, 110.0],
            index=pd.to_datetime(["2019-03-30", "2019-03-31"]),
        )
    )
    assert charts._report_period(prices) == (2019, 3)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("report_month_start", pd.Timestamp("2019-03-01")),
        ("report_year_start", pd.Timestamp("2019-01-01")),
    ],
)
def test_relative_filter_dates_come_from_the_dataset(token, expected):
    dates = pd.to_datetime(["2019-03-30", "2019-03-31"])
    assert charts._resolve_filter_start_date(token, dates) == expected


def test_return_comparison_templates_use_report_period_filters():
    assert charts.mtd_return["filter_start_date"] == "report_month_start"
    assert charts.ytd_return["filter_start_date"] == "report_year_start"
    assert charts.ytd_return_full["filter_start_date"] == "report_year_start"


def test_earliest_plotted_year_can_still_reach_its_baseline(monkeypatch):
    """The min-year filter restricts what is plotted, not what baselines are visible.

    2014 is the first plotted year, so its baseline necessarily comes from 2013 — below
    the cutoff. Filtering the price series before the lookup would silently drop it.
    """
    _disable_writes(monkeypatch)
    dates = pd.to_datetime(
        ["2013-07-31", "2014-08-01", "2014-08-02", "2015-07-31", "2015-08-01"]
    )
    data = pd.DataFrame(
        {"price_close": [100.0, 150.0, 160.0, 200.0, 220.0]}, index=dates
    )

    figure = charts.create_monthly_returns(data)
    names = {trace.name for trace in figure.data}

    # 2014 is plotted, measured from the 2013-07-31 close of 100 — a 50% day one.
    assert "2014" in names
    assert _trace(figure, 2014).y[0] == pytest.approx(50.0)
    # And the current period still measures from its own prior close of 200.
    assert _trace(figure, 2015).y[0] == pytest.approx(10.0)


def test_period_baseline_rejects_nonpositive_and_missing_closes():
    prices = charts._positive_price_series(
        pd.Series(
            [100.0, 120.0], index=pd.to_datetime(["2025-08-01", "2025-08-02"])
        )
    )
    # Nothing exists before August 2025, so there is no baseline to index against.
    assert charts._period_baseline(prices, 2025, 8) is None
    assert charts._period_baseline(prices, 2025) is None
