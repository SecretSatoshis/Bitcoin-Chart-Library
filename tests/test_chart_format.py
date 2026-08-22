import datetime

import numpy as np
import pandas as pd
import pytest

import chart_format as charts


def _disable_writes(monkeypatch):
    monkeypatch.setattr(charts, "save_chart_html", lambda fig, filename: None)


def _set_today(monkeypatch, year, month, day):
    class FixedDate(datetime.date):
        @classmethod
        def today(cls):
            return cls(year, month, day)

    monkeypatch.setattr(charts.datetime, "date", FixedDate)


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
    today = datetime.date.today()
    dates = pd.to_datetime(
        [
            f"{today.year - 1}-{today.month:02d}-01",
            f"{today.year - 1}-{today.month:02d}-03",
            f"{today.year}-{today.month:02d}-01",
            f"{today.year}-{today.month:02d}-03",
        ]
    )
    data = pd.DataFrame({"price_close": [100, 120, 200, 260]}, index=dates)

    figure = charts.create_monthly_returns(data)
    current_trace = _trace(figure, today.year)

    assert np.isnan(current_trace.y[1])
    assert pd.Timestamp(current_trace.x[2]).day == 3
    assert current_trace.y[2] == pytest.approx(30.0)


def test_indexed_monthly_returns_reject_missing_current_month(monkeypatch):
    _disable_writes(monkeypatch)
    today = datetime.date.today()
    data = pd.DataFrame(
        {"price_close": [100, 110]},
        index=pd.to_datetime(
            [f"{today.year - 1}-{today.month:02d}-01", f"{today.year - 1}-{today.month:02d}-02"]
        ),
    )

    with pytest.raises(ValueError, match="refusing to leave an older indexed MTD chart"):
        charts.create_indexed_monthly_returns(data)


def test_yearly_returns_preserve_missing_calendar_days(monkeypatch):
    _disable_writes(monkeypatch)
    today = datetime.date.today()
    data = pd.DataFrame(
        {"price_close": [100, 130]},
        index=pd.to_datetime([f"{today.year}-01-01", f"{today.year}-01-03"]),
    )

    figure = charts.create_yearly_returns(data)
    current_trace = _trace(figure, today.year)

    assert np.isnan(current_trace.y[1])
    third_date = pd.Timestamp(current_trace.x[2])
    assert third_date.month == 1 and third_date.day == 3
    assert current_trace.y[2] == pytest.approx(30.0)


def test_indexed_yearly_returns_reject_missing_current_year(monkeypatch):
    _disable_writes(monkeypatch)
    today = datetime.date.today()
    data = pd.DataFrame(
        {"price_close": [100, 110]},
        index=pd.to_datetime([f"{today.year - 1}-01-01", f"{today.year - 1}-12-31"]),
    )

    with pytest.raises(ValueError, match=f"No price data is available for {today.year}"):
        charts.create_indexed_yearly_returns(data)


def test_indexed_yearly_returns_skip_partial_historical_year(monkeypatch):
    _disable_writes(monkeypatch)
    today = datetime.date.today()
    prior_dates = pd.date_range(f"{today.year - 1}-01-01", f"{today.year - 1}-01-31")
    current_dates = pd.to_datetime([f"{today.year}-01-01", f"{today.year}-01-02"])
    dates = prior_dates.append(current_dates)
    data = pd.DataFrame({"price_close": np.arange(1, len(dates) + 1)}, index=dates)

    figure = charts.create_indexed_yearly_returns(data)

    assert str(today.year - 1) not in {trace.name for trace in figure.data}
    assert str(today.year) in {trace.name for trace in figure.data}


def test_indexed_yearly_reference_dates_exclude_leap_day(monkeypatch):
    _disable_writes(monkeypatch)
    _set_today(monkeypatch, 2024, 3, 1)
    data = pd.DataFrame(
        {"price_close": [100, 120]},
        index=pd.to_datetime(["2024-01-01", "2024-03-01"]),
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
