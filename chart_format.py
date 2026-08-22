import plotly.graph_objects as go
import pandas as pd
import os
import numpy as np
import datetime
import base64
import calendar
import html as html_module
import re
import warnings
from pathlib import Path

# Get the first day of the current month
first_day_of_month = pd.Timestamp.now().replace(day=1).strftime("%Y-%m-%d")
# Get the current month and year for chart title
current_month_year = pd.Timestamp.now().strftime("%B %Y")  # Example: "October 2024"
# Get current year
current_year = pd.Timestamp.now().year


def _logo_data_uri():
    """Return the bundled logo as a self-contained PNG data URI."""
    logo_path = Path(__file__).with_name("Secret_Satoshis_Logo.png")
    encoded_logo = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_logo}"


def _price_series(selected_metrics):
    """Return one sorted, numeric Bitcoin price per normalized calendar day."""
    if "price_close" not in selected_metrics.columns:
        raise KeyError("selected_metrics must contain a 'price_close' column.")

    prices = pd.to_numeric(selected_metrics["price_close"], errors="coerce").copy()
    index = pd.to_datetime(prices.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    prices.index = index.normalize()
    prices = prices.sort_index()
    prices = prices.groupby(level=0).last().dropna()
    if prices.empty:
        raise ValueError("No valid Bitcoin price data is available.")
    return prices


def _reference_year_dates(year):
    """Return all 365 month/day slots for a year, excluding February 29."""
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    return dates[~((dates.month == 2) & (dates.day == 29))]


def _map_to_reference_year(series, reference_year):
    """Map a dated series to the same month/day in a reference year."""
    mapped = series.copy()
    mapped.index = pd.DatetimeIndex(
        [pd.Timestamp(reference_year, date.month, date.day) for date in series.index]
    )
    return mapped


def _is_complete_non_leap_year(series):
    """Return whether a series has every calendar day except February 29."""
    if len(series) != 365:
        return False
    first = series.index[0]
    last = series.index[-1]
    return (first.month, first.day) == (1, 1) and (last.month, last.day) == (12, 31)


def save_chart_html(fig, filename):
    """
    Persist an interactive chart as HTML.

    `include_plotlyjs="directory"` writes a single shared Charts/plotly.min.js and has
    every chart reference it relatively. Plotly's default (True) inlines a complete
    ~4.6 MB copy of plotly.js into each file — across 50+ charts that is ~257 MB of
    byte-identical duplication, and a reader who opens three charts downloads the same
    bundle three times because each is a separate document.

    "directory" is preferred over "cdn" here: it keeps the library self-hosted, so
    there is no third-party request from readers' browsers and no external dependency,
    and the charts still work offline as long as the folder is intact. All charts are
    already served together from GitHub Pages, so the shared-directory assumption holds.
    """
    html_directory = "Charts"
    os.makedirs(html_directory, exist_ok=True)
    html_filepath = os.path.join(html_directory, f"{filename}.html")
    fig.write_html(html_filepath, auto_open=False, include_plotlyjs="directory")

    raw_title = getattr(getattr(fig.layout, "title", None), "text", None)
    document_title = raw_title or filename.replace("_", " ")
    document_title = re.sub(r"<[^>]+>", " ", str(document_title))
    document_title = " ".join(html_module.unescape(document_title).split())
    title_markup = (
        f"<title>{html_module.escape(document_title)} | Secret Satoshis</title>"
    )
    chart_html = Path(html_filepath).read_text(encoding="utf-8")
    chart_html = chart_html.replace("</head>", f"{title_markup}</head>", 1)
    Path(html_filepath).write_text(chart_html, encoding="utf-8")
    return html_filepath


def get_price_on_or_after(selected_metrics, date, price_col="price_close"):
    """Return the first available Bitcoin price on or after a target date."""
    if selected_metrics is None:
        raise ValueError("selected_metrics is required when scaling a chart to Bitcoin price.")

    metrics = selected_metrics.copy()
    if not isinstance(metrics.index, pd.DatetimeIndex):
        metrics.index = pd.to_datetime(metrics.index)
    metrics = metrics.sort_index()

    target_date = pd.to_datetime(date)
    target_date = target_date.tz_localize(None) if target_date.tzinfo else target_date
    if metrics.index.tz is not None:
        metrics.index = metrics.index.tz_localize(None)

    values = metrics.loc[metrics.index >= target_date, price_col].dropna()
    if values.empty:
        raise ValueError(f"No {price_col} value available on or after {target_date.date()}.")

    return float(values.iloc[0])


# =============================================================================
# CHART CONSTANTS
# =============================================================================

# Standard color palette for chart lines
CHART_COLORS = [
    "#7149C6",  # Purple
    "#0079FF",  # Blue
    "#FF0060",  # Pink/Red
    "#22A699",  # Teal
    "#8c564b",  # Brown
    "#e377c2",  # Light pink
    "#7f7f7f",  # Gray
    "#bcbd22",  # Olive
    "#17becf",  # Cyan
]

# Bitcoin's signature orange color
BITCOIN_ORANGE = "#FF9900"

# Branding configuration
BRANDING_CONFIG = {
    "watermark_text": "SecretSatoshis.com",
    "watermark_font_size": 50,
    "watermark_color": "rgba(128, 128, 128, 0.5)",
    "logo_url": _logo_data_uri(),
    "logo_x": 0.0,
    "logo_y": 1.2,
    "logo_size": 0.1,
}

# Standard chart layout settings
BASE_CHART_LAYOUT = dict(
    height=700,
    margin=dict(l=80, r=100, b=180, t=100, pad=2),
    font=dict(family="PT Sans Narrow", size=14, color="black"),
    template="plotly_white",
    plot_bgcolor="rgba(255, 255, 255, 1)",
    hovermode="x",
    autosize=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.12,
        xanchor="center",
        x=0.5,
    ),
)

# Bitcoin historical events for chart annotations
BITCOIN_HISTORICAL_EVENTS = [
    {
        "name": "Halving",
        "dates": ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20"],
        "orientation": "v",
    },
    {"name": "MtGox Launch", "dates": ["2010-07-01"], "orientation": "v"},
    {"name": "MtGox Hack", "dates": ["2011-06-11"], "orientation": "v"},
    {"name": "MtGox Bankrupt", "dates": ["2014-02-01"], "orientation": "v"},
    {"name": "BitLicense", "dates": ["2015-08-08"], "orientation": "v"},
    {"name": "CME Futures", "dates": ["2017-12-17"], "orientation": "v"},
    {"name": "Bitcoin Winter", "dates": ["2018-12-15"], "orientation": "v"},
    {"name": "Coinbase IPO", "dates": ["2021-04-14"], "orientation": "v"},
    {"name": "FTX Bankrupt", "dates": ["2022-11-11"], "orientation": "v"},
    {"name": "Spot ETF Launch", "dates": ["2024-01-11"], "orientation": "v"},
    {
        "name": "U.S. Strategic Bitcoin Reserve",
        "dates": ["2025-03-06"],
        "orientation": "v",
    },
    {
        "name": "Strategy Sells Bitcoin",
        "dates": ["2026-06-29"],
        "orientation": "v",
    },
]

# Events with only halvings (for supply-focused charts)
HALVING_EVENTS = [
    {
        "name": "Halving",
        "dates": ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20"],
        "orientation": "v",
    },
]


def add_branding(
    fig,
    data_source="Data Source: BRK (bitview.space)",
    source_y=-0.3,
):
    """
    Add standard branding elements to a Plotly figure.

    Adds:
    - Watermark text in center
    - Logo image in top-left
    - Data source annotation in bottom-right

    Args:
        fig: Plotly Figure object
        data_source: Text for data source attribution
        source_y: Vertical paper coordinate for the source attribution

    Returns:
        fig: Modified figure with branding added
    """
    # Add watermark annotation
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        text=BRANDING_CONFIG["watermark_text"],
        showarrow=False,
        font=dict(
            size=BRANDING_CONFIG["watermark_font_size"],
            color=BRANDING_CONFIG["watermark_color"],
        ),
        align="center",
    )

    # Add logo image
    fig.add_layout_image(
        dict(
            source=BRANDING_CONFIG["logo_url"],
            x=BRANDING_CONFIG["logo_x"],
            y=BRANDING_CONFIG["logo_y"],
            sizex=BRANDING_CONFIG["logo_size"],
            sizey=BRANDING_CONFIG["logo_size"],
            xanchor="left",
            yanchor="top",
        )
    )

    # Add data source annotation
    fig.add_annotation(
        text=data_source,
        xref="paper",
        yref="paper",
        x=1,
        y=source_y,
        xanchor="right",
        yanchor="bottom",
        showarrow=False,
        font=dict(family="PT Sans Narrow", size=12, color="#666"),
        align="right",
    )

    return fig


def create_line_chart(chart_template, selected_metrics):
    # Extract the start and end dates from the template and filter the data accordingly
    if "filter_start_date" in chart_template:
        start_date = pd.to_datetime(chart_template["filter_start_date"])

        # Set end_date to filter_end_date if specified, otherwise use the maximum date available in the data
        end_date = pd.to_datetime(
            chart_template.get("filter_end_date", selected_metrics.index.max())
        )

        # Ensure the index is of datetime type for proper filtering
        selected_metrics.index = pd.to_datetime(selected_metrics.index)

        # Apply the date filter to the index (time) of the entire dataset and ensure all fields are filtered
        selected_metrics = selected_metrics.loc[start_date:end_date]

    # Extract basic chart details from the template
    x = selected_metrics.index
    y_data = chart_template["y_data"]
    title = chart_template["title"]
    x_label = chart_template["x_label"]
    y1_label = chart_template["y1_label"]
    y2_label = chart_template["y2_label"]
    filename = chart_template["filename"]
    y1_type = chart_template.get("y1_type", "log")
    y2_type = chart_template.get("y2_type", "linear")
    data_source_text = chart_template["data_source"]

    plottable_y_data = []
    for y_item in y_data:
        metric = y_item["data"]
        if metric in selected_metrics.columns:
            plottable_y_data.append(y_item)
        elif y_item.get("optional", False):
            warnings.warn(
                f"Skipping optional metric {metric!r} in chart {filename!r}; "
                "the selected data source does not provide it.",
                RuntimeWarning,
                stacklevel=2,
            )
        else:
            raise KeyError(f"Chart {filename!r} requires missing metric {metric!r}.")

    has_y2 = any(
        y_item.get("yaxis", "y") == "y2" for y_item in plottable_y_data
    )

    # Initialize a Plotly Figure object
    fig = go.Figure()

    # Iterate over each data series to add line traces to the figure
    for i, y_item in enumerate(plottable_y_data):
        # Assign a color for the line, using Bitcoin orange for 'price_close'
        line_color = (
            CHART_COLORS[i % len(CHART_COLORS)]
            if y_item["data"] != "price_close"
            else BITCOIN_ORANGE
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=selected_metrics[y_item["data"]],
                mode="lines",
                name=y_item.get("name", y_item["data"]),
                line=dict(color=line_color),
                yaxis=y_item.get("yaxis", "y"),
                hovertemplate="%{y:,.2f} %{fullData.name}<extra></extra>",
            )
        )

    axis_buttons = [
        dict(
            label="Y1-axis: Linear",
            method="relayout",
            args=["yaxis.type", "linear"],
        ),
        dict(
            label="Y1-axis: Log",
            method="relayout",
            args=["yaxis.type", "log"],
        ),
    ]
    if has_y2:
        axis_buttons.extend(
            [
                dict(
                    label="Y2-axis: Linear",
                    method="relayout",
                    args=["yaxis2.type", "linear"],
                ),
                dict(
                    label="Y2-axis: Log",
                    method="relayout",
                    args=["yaxis2.type", "log"],
                ),
            ]
        )

    layout = dict(
        title=dict(text=title, x=0.5, xanchor="center", y=0.98),
        # Datetime tick labels already make the axis clear, and the redundant
        # "Date" title collides with the legend on charts with many traces.
        xaxis_title=None if str(x_label).casefold() == "date" else x_label,
        yaxis_title=y1_label,
        yaxis=dict(showgrid=False, type=y1_type, autorange=True, automargin=True),
        xaxis=dict(
            showgrid=False,
            tickformat="%B-%d-%Y",
            rangeslider_visible=False,
            automargin=True,
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(count=2, label="2y", step="year", stepmode="backward"),
                    dict(count=3, label="3y", step="year", stepmode="backward"),
                    dict(count=5, label="5y", step="year", stepmode="backward"),
                    dict(count=10, label="10y", step="year", stepmode="backward"),
                    dict(step="all"),
                ]
            ),
            autorange=True,
        ),
        updatemenus=[
            go.layout.Updatemenu(
                buttons=axis_buttons,
                showactive=False,
                type="buttons",
                direction="right",
                x=0,
                xanchor="left",
                y=chart_template.get("controls_y", -0.2),
                yanchor="top",
            )
        ],
    )
    if has_y2:
        layout["yaxis2"] = dict(
            title=y2_label,
            overlaying="y",
            side="right",
            showgrid=False,
            type=y2_type,
            autorange=True,
            automargin=True,
        )

    # Allow especially dense templates to reserve extra space without changing
    # the proportions of every chart in the library.
    common_layout = {
        **BASE_CHART_LAYOUT,
        "height": chart_template.get("height", BASE_CHART_LAYOUT["height"]),
        "margin": {
            **BASE_CHART_LAYOUT["margin"],
            "b": chart_template.get(
                "bottom_margin", BASE_CHART_LAYOUT["margin"]["b"]
            ),
        },
        "legend": {
            **BASE_CHART_LAYOUT["legend"],
            "y": chart_template.get("legend_y", BASE_CHART_LAYOUT["legend"]["y"]),
            "yanchor": chart_template.get(
                "legend_yanchor", BASE_CHART_LAYOUT["legend"]["yanchor"]
            ),
            "font": {
                "size": chart_template.get("legend_font_size", 14),
            },
        },
    }

    # Update figure layout with common styling and customization.
    fig.update_layout(**layout, **common_layout)

    # Format the y-axis with comma as thousand separator
    fig.update_layout(yaxis=dict(tickformat=",.2f"))

    # Add event annotations and vertical lines if defined in the chart template
    if "events" in chart_template:
        for index, event in enumerate(chart_template["events"]):
            event_dates = pd.to_datetime(event["dates"])
            for date in event_dates:
                if event.get("orientation", "v") == "v":  # vertical line
                    fig.add_shape(
                        type="line",
                        xref="x",
                        yref="paper",
                        x0=date.strftime("%Y-%m-%d"),
                        y0=0,
                        x1=date.strftime("%Y-%m-%d"),
                        y1=1,
                        line=dict(color="black", width=1, dash="dash"),
                    )
                # Position annotations in paper coordinates (0-1 of plot height), the
                # same reference the vertical line above uses.
                #
                # This previously derived a y value from the data by scanning every
                # numeric column of the full master frame — not the series actually
                # plotted — and multiplying the global maximum by 1.05. That was wrong
                # three ways: it picked up unrelated columns, it recomputed a constant
                # once per event date inside the loop, and on a log axis Plotly reads
                # annotation y in log10 units, so a raw price was always mispositioned.
                # It also produced `inf` whenever any column held a non-finite value,
                # which Plotly serializes as null — leaving every event label on the
                # chart unpositioned.
                fig.add_annotation(
                    x=pd.to_datetime(date)
                    + pd.DateOffset(
                        days=5
                    ),  # Move annotation slightly to the right of the line
                    y=event.get("annotation_y", 0.98),
                    text=event["name"],
                    showarrow=False,
                    font=dict(
                        color="black",
                        size=event.get("annotation_font_size", 14),
                    ),
                    xshift=event.get("annotation_xshift", 0),
                    xanchor="left",  # Align text to the left, which shifts it to the right of the line
                    yanchor="top",
                    xref="x",
                    yref="paper",
                    textangle=90,  # Rotate annotation by 90 degrees
                )

    # Add branding elements (watermark, logo, data source)
    add_branding(
        fig,
        data_source_text,
        source_y=chart_template.get("source_y", -0.3),
    )

    return fig


def create_days_since_chart(
    df: pd.DataFrame,
    chart_template: dict,
    selected_metrics: pd.DataFrame | None = None,
):
    """
    Universal small-multiples overlay function.

    Requires df to contain:
      - chart_template["x_data"]
      - chart_template["value_col"]
      - chart_template["group_col"]

    Each trace is defined by chart_template["y_data"] entries with:
      - "name": label shown in legend
      - "group": value in df[group_col] to filter
    """
    x_col = chart_template["x_data"]
    y_col = chart_template.get("value_col", "index_value")
    g_col = chart_template.get("group_col", "Era")
    price_scale = chart_template.get("price_scale")
    y_multiplier = 1.0
    if price_scale:
        y_multiplier = get_price_on_or_after(
            selected_metrics,
            price_scale["anchor_date"],
            price_scale.get("price_col", "price_close"),
        )

    required = {x_col, y_col, g_col}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(
            f"Missing columns in df: {missing}. "
            f"Expected columns include {required}. Got columns: {list(df.columns)}"
        )

    fig = go.Figure()

    # Plot each series from its own filtered subset (prevents NaN mixing)
    for i, series in enumerate(chart_template["y_data"]):
        group_val = series.get("group")
        if group_val is None:
            raise KeyError("Each y_data entry must include a 'group' key.")

        d = df.loc[df[g_col] == group_val, [x_col, y_col]].dropna()
        if d.empty:
            continue

        # optional: sort by x for clean lines
        d = d.sort_values(x_col)
        y_values = d[y_col] * y_multiplier

        fig.add_trace(
            go.Scatter(
                x=d[x_col],
                y=y_values,
                mode="lines",
                name=series["name"],
                line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=2),
                hovertemplate=chart_template.get(
                    "hovertemplate",
                    "%{y:,.2f}<extra>%{fullData.name}</extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=chart_template["title"], x=0.5, xanchor="center", y=0.98),
        xaxis_title=(
            None
            if str(chart_template["x_label"]).casefold() == "date"
            else chart_template["x_label"]
        ),
        yaxis_title=chart_template["y1_label"],
        yaxis=dict(
            type=chart_template.get("y1_type", "linear"),
            showgrid=False,
            automargin=True,
        ),
        updatemenus=[
            go.layout.Updatemenu(
                buttons=[
                    dict(label="Y1-axis: Linear", method="relayout", args=["yaxis.type", "linear"]),
                    dict(label="Y1-axis: Log",    method="relayout", args=["yaxis.type", "log"]),
                ],
                showactive=False,
                type="buttons",
                direction="right",
                x=0,
                xanchor="left",
                y=-0.2,
                yanchor="top",
            )
        ],
        **BASE_CHART_LAYOUT,
    )

    # y tick formatting: you can override per-chart in template if needed
    fig.update_yaxes(
        tickformat=chart_template.get("y_tickformat", "~g"),
        autorange=True
    )
    fig.update_xaxes(autorange=True, automargin=True)

    # Add branding elements (watermark, logo, data source)
    add_branding(fig, chart_template.get("data_source", ""))

    filename = chart_template.get("filename", "chart")
    save_chart_html(fig, filename)

    return fig


def create_monthly_returns(selected_metrics):
    """
    Plot the daily month-to-date (MTD) returns for the current month across multiple years,
    with the current year's daily progression, the median, and the average MTD return
    across historical years.

    Parameters:
    selected_metrics (pd.DataFrame): DataFrame containing Bitcoin price data with a 'price_close' column.

    Returns:
    fig (go.Figure): Plotly figure object with the historical performance chart.
    """
    # Automatically detect the current month and year
    today = datetime.date.today()
    current_year = today.year
    current_month = today.month

    prices = _price_series(selected_metrics)
    prices = prices[prices.index.year >= 2014]

    # Dictionary to store daily MTD returns for each year within the current month
    daily_mtd_returns = {}

    # Calculate MTD returns up to each day of the current month for each year
    for year in prices.index.year.unique():
        monthly_prices = prices[
            (prices.index.month == current_month) & (prices.index.year == year)
        ]

        if not monthly_prices.empty:
            # Calculate daily MTD return for each day of the month
            daily_returns = (monthly_prices / monthly_prices.iloc[0] - 1) * 100
            daily_returns.index = monthly_prices.index.day
            daily_mtd_returns[year] = daily_returns

    if not daily_mtd_returns:
        raise ValueError(f"No price data is available for calendar month {current_month}.")

    # Align by actual day-of-month so missing source days remain missing instead of
    # shifting every subsequent value one day to the left.
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    day_numbers = range(1, days_in_month + 1)
    daily_mtd_df = pd.DataFrame(daily_mtd_returns, index=day_numbers)
    daily_mtd_df.index = pd.DatetimeIndex(
        [pd.Timestamp(current_year, current_month, day) for day in day_numbers]
    )

    # Calculate the median and average MTD return for each day across historical years (excluding the current year)
    historical_df = daily_mtd_df.drop(columns=[current_year], errors="ignore")
    median_mtd_returns = historical_df.median(axis=1)
    average_mtd_returns = historical_df.mean(axis=1)

    # Initialize Plotly Figure
    fig = go.Figure()

    # Define color scheme for specific lines
    current_year_color = "rgb(255,153,0)"  # Orange for the current year
    median_color = "black"  # Black for the median line
    average_color = "green"  # Green for the average line

    # Plot historical MTD data for each year
    for year in historical_df.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_mtd_df.index,
                y=daily_mtd_df[year],
                mode="lines",
                name=str(year),
                line=dict(width=1),
                hovertemplate="MTD Return (%) %{y:,.2f} | %{fullData.name}<extra></extra>",
                opacity=0.3,
            )
        )

    # Plot the current year's MTD progression in orange
    if current_year in daily_mtd_df.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_mtd_df.index,
                y=daily_mtd_df[current_year],
                mode="lines",
                name=str(current_year),
                line=dict(color=current_year_color, width=3),
                hovertemplate="MTD Return (%) %{y:,.2f} | %{fullData.name}<extra></extra>",
                opacity=1,
            )
        )

    # Plot the median MTD return for historical data as a black dashed line
    fig.add_trace(
        go.Scatter(
            x=daily_mtd_df.index,
            y=median_mtd_returns,
            mode="lines",
            name="Median MTD Return",
            line=dict(color=median_color, width=2, dash="dash"),
            hovertemplate="Median: %{y:,.2f}%<extra></extra>",
            opacity=0.9,
        )
    )

    # Plot the average MTD return for historical data as a green solid line
    fig.add_trace(
        go.Scatter(
            x=daily_mtd_df.index,
            y=average_mtd_returns,
            mode="lines",
            name="Average MTD Return",
            line=dict(color=average_color, width=2),
            hovertemplate="Average: %{y:,.2f}%<extra></extra>",
            opacity=0.9,
        )
    )

    # Set up layout and axis titles to match the styling template
    month_name = datetime.date(1900, current_month, 1).strftime("%B")
    fig.update_layout(
        title=dict(
            text=f"Bitcoin {month_name} MTD Returns Comparison Since {prices.index.year.min()}",
            x=0.5,
            xanchor="center",
            y=0.98,
        ),
        xaxis_title=None,
        yaxis_title="MTD Return (%)",
        yaxis=dict(showgrid=False, tickformat=",.2f", autorange=True),
        xaxis=dict(
            showgrid=False,
            tickformat="%b %d",
            rangeslider_visible=False,
            autorange=True,
        ),
        **BASE_CHART_LAYOUT,
    )

    # Add branding elements (watermark, logo, data source)
    add_branding(fig, "Data Source: Bitview")

    save_chart_html(fig, "MTD_Return_By_Year_Percentage")

    return fig


def create_indexed_monthly_returns(selected_metrics):
    """
    Plot the daily month-to-date (MTD) returns for the current month, indexed to the current month's starting price,
    across multiple years. Includes average and median monthly returns.

    Parameters:
    selected_metrics (pd.DataFrame): DataFrame containing Bitcoin price data with a 'price_close' column.

    Returns:
    fig (go.Figure): Plotly figure object with the historical performance chart.
    """
    prices = _price_series(selected_metrics)
    prices = prices[prices.index.year >= 2014]

    # Get the current month and year for plotting and data indexing
    today = datetime.date.today()
    current_year = today.year
    current_month = today.month

    # Dictionary to store indexed MTD prices for each year
    indexed_mtd_prices = {}

    # Get the starting price for the current month to index other years
    current_month_data = prices[
        (prices.index.year == current_year) & (prices.index.month == current_month)
    ]
    if current_month_data.empty:
        raise ValueError(
            f"No price data is available for {current_year}-{current_month:02d}; "
            "refusing to leave an older indexed MTD chart in place."
        )

    current_start_price = current_month_data.iloc[0]

    # Calculate indexed MTD prices for each year based on the current month's starting price
    for year in prices.index.year.unique():
        monthly_data = prices[
            (prices.index.year == year) & (prices.index.month == current_month)
        ]

        if not monthly_data.empty:
            # Scale each year's monthly price series to the current year's monthly starting price
            indexed_prices = monthly_data / monthly_data.iloc[0] * current_start_price
            indexed_prices.index = monthly_data.index.day
            indexed_mtd_prices[year] = indexed_prices

    days_in_month = calendar.monthrange(current_year, current_month)[1]
    day_numbers = range(1, days_in_month + 1)
    daily_mtd_df = pd.DataFrame(indexed_mtd_prices, index=day_numbers)
    daily_mtd_df.index = pd.DatetimeIndex(
        [pd.Timestamp(current_year, current_month, day) for day in day_numbers]
    )

    # Exclude the current year from median and average calculations
    historical_df = daily_mtd_df.drop(columns=[current_year], errors="ignore")
    median_mtd_returns = historical_df.median(axis=1)
    average_mtd_returns = historical_df.mean(axis=1)

    # Initialize Plotly Figure
    fig = go.Figure()

    # Define color scheme
    current_year_color = "rgb(255,153,0)"  # Orange for the current year
    median_color = "black"  # Black for the median line
    average_color = "green"  # Green for the average line

    # Plot historical MTD data for each year
    for year in historical_df.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_mtd_df.index,
                y=daily_mtd_df[year],
                mode="lines",
                name=str(year),
                hovertemplate="MTD Return ($) %{y:,.2f} | %{fullData.name}<extra></extra>",
                opacity=0.3,
            )
        )

    # Plot the current year's MTD progression
    if current_year in daily_mtd_df.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_mtd_df.index,
                y=daily_mtd_df[current_year],
                mode="lines",
                name=str(current_year),
                line=dict(color=current_year_color, width=3),
                hovertemplate="MTD Return ($) %{y:,.2f} | %{fullData.name}<extra></extra>",
                opacity=1,
            )
        )

    # Plot the median MTD return for historical data as a black dashed line
    fig.add_trace(
        go.Scatter(
            x=daily_mtd_df.index,
            y=median_mtd_returns,
            mode="lines",
            name="Median MTD Return",
            line=dict(color=median_color, width=2, dash="dash"),
            hovertemplate="Median: %{y:,.2f}<extra></extra>",
            opacity=0.9,
        )
    )

    # Plot the average MTD return for historical data as a green solid line
    fig.add_trace(
        go.Scatter(
            x=daily_mtd_df.index,
            y=average_mtd_returns,
            mode="lines",
            name="Average MTD Return",
            line=dict(color=average_color, width=2),
            hovertemplate="Average: %{y:,.2f}<extra></extra>",
            opacity=0.9,
        )
    )

    # Set up layout and axis titles to match the styling template
    month_name = today.strftime("%B")
    fig.update_layout(
        title=dict(
            text=f"Bitcoin {month_name} MTD Returns Comparison (Indexed to Current Year)",
            x=0.5,
            xanchor="center",
            y=0.98,
        ),
        xaxis_title=None,
        yaxis_title="MTD Return Indexed to Current Year Start ($)",
        xaxis=dict(showgrid=False, tickformat="%b %d", rangeslider_visible=False),
        yaxis=dict(showgrid=False, tickformat=",.2f"),
        **BASE_CHART_LAYOUT,
    )

    # Add branding elements (watermark, logo, data source)
    add_branding(fig, "Data Source: Bitview")

    save_chart_html(fig, "Bitcoin_MTD_Return_By_Month_Indexed")

    return fig


def create_yearly_returns(selected_metrics):
    """
    Plot the daily year-to-date (YTD) returns for each year,
    with the current year's daily progression, the median, and the average YTD return
    across historical years.

    Parameters:
    selected_metrics (pd.DataFrame): DataFrame containing Bitcoin price data with a 'price_close' column.

    Returns:
    fig (go.Figure): Plotly figure object with the historical performance chart.
    """
    prices = _price_series(selected_metrics)
    prices = prices[prices.index.year >= 2014]
    prices = prices[~((prices.index.month == 2) & (prices.index.day == 29))]

    # Get today's year and define the current year
    today = datetime.date.today()
    current_year = today.year

    # Dictionary to store daily YTD returns for each year
    daily_ytd_returns = {}

    # Calculate YTD returns up to each day of the year for each year
    for year in prices.index.year.unique():
        yearly_data = prices[prices.index.year == year]

        starts_on_january_1 = not yearly_data.empty and (
            yearly_data.index[0].month, yearly_data.index[0].day
        ) == (1, 1)
        if not starts_on_january_1:
            continue
        if year != current_year and not _is_complete_non_leap_year(yearly_data):
            continue

        daily_returns = (yearly_data / yearly_data.iloc[0] - 1) * 100
        daily_ytd_returns[year] = _map_to_reference_year(daily_returns, current_year)

    if not daily_ytd_returns:
        raise ValueError("No complete yearly price series is available for YTD comparison.")

    # Align each observation by its true month/day, excluding February 29 even
    # when the current year is a leap year.
    date_range = _reference_year_dates(current_year)
    daily_ytd_df = pd.DataFrame(daily_ytd_returns, index=date_range)

    # Calculate median and average YTD return for each day across historical years
    historical_df = daily_ytd_df.drop(columns=[current_year], errors="ignore")
    median_ytd_returns = historical_df.median(axis=1)
    average_ytd_returns = historical_df.mean(axis=1)

    # Initialize Plotly Figure
    fig = go.Figure()

    # Plot historical YTD data for each year with default Plotly color cycle
    for year in historical_df.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_ytd_df.index,
                y=daily_ytd_df[year],
                mode="lines",
                name=str(year),
                line=dict(width=1),
                hovertemplate="YTD Return (%) %{y:,.2f} | %{fullData.name}<extra></extra>",
                opacity=0.6,
            )
        )

    # Plot the current year's YTD progression
    if current_year in daily_ytd_df.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_ytd_df.index,
                y=daily_ytd_df[current_year],
                mode="lines",
                name=str(current_year),
                line=dict(color="rgb(255,153,0)", width=3),
                hovertemplate="YTD Return (%) %{y:,.2f} | %{fullData.name}<extra></extra>",
                opacity=1,
            )
        )

    # Plot median and average YTD returns
    fig.add_trace(
        go.Scatter(
            x=daily_ytd_df.index,
            y=median_ytd_returns,
            mode="lines",
            name="Median YTD Return",
            line=dict(color="black", width=2, dash="dash"),
            hovertemplate="Median: %{y:,.2f}%<extra></extra>",
            opacity=0.9,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_ytd_df.index,
            y=average_ytd_returns,
            mode="lines",
            name="Average YTD Return",
            line=dict(color="green", width=2),
            hovertemplate="Average: %{y:,.2f}%<extra></extra>",
            opacity=0.9,
        )
    )

    # Layout setup
    fig.update_layout(
        title=dict(
            text=f"Bitcoin YTD Returns Comparison Since {prices.index.year.min()}",
            x=0.5,
            xanchor="center",
            y=0.98,
        ),
        xaxis_title=None,
        yaxis_title="YTD Return (%)",
        xaxis=dict(showgrid=False, tickformat="%b %d"),
        yaxis=dict(showgrid=False, tickformat=",.2f"),
        **BASE_CHART_LAYOUT,
    )

    # Add branding elements (watermark, logo, data source)
    add_branding(fig, "Data Source: Bitview")

    save_chart_html(fig, "Bitcoin_YTD_Return_By_Year_Percentage")

    return fig


def create_indexed_yearly_returns(selected_metrics):
    """
    Plot the daily year-to-date (YTD) returns for each year, indexed to the current year's starting price.
    This allows for a dollar-comparison of annual performance across multiple years, and also includes
    average and median yearly returns for years with full data.

    Parameters:
    selected_metrics (pd.DataFrame): DataFrame containing Bitcoin price data with a 'price_close' column.

    Returns:
    fig (go.Figure): Plotly figure object with the historical performance chart in dollar terms.
    """
    prices = _price_series(selected_metrics)
    prices = prices[prices.index.year >= 2014]
    prices = prices[~((prices.index.month == 2) & (prices.index.day == 29))]

    # Get today's year and define the current year for the chart
    today = datetime.date.today()
    current_year = today.year

    # Dictionary to store indexed YTD prices for each year
    indexed_ytd_prices = {}

    current_year_prices = prices[prices.index.year == current_year]
    if current_year_prices.empty:
        raise ValueError(
            f"No price data is available for {current_year}; refusing to leave an "
            "older indexed YTD chart in place."
        )
    if (current_year_prices.index[0].month, current_year_prices.index[0].day) != (1, 1):
        raise ValueError(f"Price data for {current_year} does not start on January 1.")
    current_start_price = current_year_prices.iloc[0]

    # Calculate indexed YTD prices for each year based on the current year's starting price
    for year in prices.index.year.unique():
        yearly_data = prices[prices.index.year == year]

        # Historical comparisons must contain every non-leap calendar day. The
        # current year may be incomplete, but it must begin on January 1.
        if yearly_data.empty:
            continue
        if year != current_year and not _is_complete_non_leap_year(yearly_data):
            continue

        # Scale each year's price series to the current year's starting price
        indexed_prices = yearly_data / yearly_data.iloc[0] * current_start_price
        indexed_ytd_prices[year] = _map_to_reference_year(indexed_prices, current_year)

    date_range = _reference_year_dates(current_year)
    daily_ytd_df = pd.DataFrame(indexed_ytd_prices, index=date_range)
    # Exclude the current year from median and average calculations
    historical_df = daily_ytd_df.drop(columns=[current_year], errors="ignore")

    # Calculate median and average
    median_ytd_returns = historical_df.median(axis=1)
    average_ytd_returns = historical_df.mean(axis=1)

    # Initialize Plotly Figure
    fig = go.Figure()

    # Define color scheme
    historical_color = "rgba(111, 168, 220, 1)"  # Light blue
    current_year_color = "rgb(255,153,0)"  # Orange
    median_color = "black"  # Black
    average_color = "green"  # Green

    # Plot historical data using default Plotly colors
    for year in historical_df.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_ytd_df.index,
                y=daily_ytd_df[year],
                mode="lines",
                name=str(year),
                line=dict(width=1),  # Use default color cycle
                hovertemplate="YTD Return ($) %{y:,.2f} | %{fullData.name}<extra></extra>",
                opacity=0.6,
            )
        )

    # Plot current year data
    if current_year in daily_ytd_df.columns:
        fig.add_trace(
            go.Scatter(
                x=daily_ytd_df.index,
                y=daily_ytd_df[current_year],
                mode="lines",
                name=str(current_year),
                line=dict(color=current_year_color, width=3),
                hovertemplate="YTD Return ($) %{y:,.2f} | %{fullData.name}<extra></extra>",
                opacity=1,
            )
        )

    # Plot median and average lines
    fig.add_trace(
        go.Scatter(
            x=daily_ytd_df.index,
            y=median_ytd_returns,
            mode="lines",
            name="Median YTD Return",
            line=dict(color=median_color, width=2, dash="dash"),
            hovertemplate="Median: %{y:,.2f}<extra></extra>",
            opacity=0.9,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_ytd_df.index,
            y=average_ytd_returns,
            mode="lines",
            name="Average YTD Return",
            line=dict(color=average_color, width=2),
            hovertemplate="Average: %{y:,.2f}<extra></extra>",
            opacity=0.9,
        )
    )

    # Consistent layout setup
    fig.update_layout(
        title=dict(
            text=f"Bitcoin YTD Returns Comparison (Indexed to Current Year)",
            x=0.5,
            xanchor="center",
            y=0.98,
        ),
        xaxis_title=None,
        yaxis_title="Prices Indexed to Current Year Start ($)",
        xaxis=dict(showgrid=False, tickformat="%b %d", rangeslider_visible=False),
        yaxis=dict(showgrid=False, tickformat=",.2f"),
        **BASE_CHART_LAYOUT,
    )

    # Add branding elements (watermark, logo, data source)
    add_branding(fig, "Data Source: Bitview")

    save_chart_html(fig, "Bitcoin_YTD_Return_By_Year_Indexed")

    return fig


# Create Charts Function
def create_charts(selected_metrics, chart_templates):
    figures = []
    for chart_template in chart_templates:
        # Call the function to create the line chart
        fig = create_line_chart(chart_template, selected_metrics)

        # Persist the chart to disk as interactive HTML
        save_chart_html(fig, chart_template["filename"])

        # Append the figure to the list of figures
        figures.append(fig)
    return figures


# Supply Chart
chart_supply = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Supply", "data": "supply", "yaxis": "y"},
        {
            "name": "New Coins Issued 30 Day MA",
            "data": "30_day_ma_subsidy_sum_24h",
            "yaxis": "y2",
        },
        {
            "name": "New Coins Issued 365 Day MA",
            "data": "365_day_ma_subsidy_sum_24h",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin Supply & Daily Issuance",
    "x_label": "Date",
    "y1_label": "Bitcoin Supply",
    "y2_label": "New Bitcoins Created Each Day",
    "filename": "Bitcoin_Supply",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "events": HALVING_EVENTS,
}

# Transaction Chart
chart_transactions = {
    "x_data": "time",
    "y_data": [
        {"name": "Transaction Count", "data": "tx_count_sum_24h", "yaxis": "y"},
        {
            "name": "Tx Count 30 Day MA",
            "data": "30_day_ma_tx_count_sum_24h",
            "yaxis": "y",
        },
        {
            "name": "Tx Count 365 Day MA",
            "data": "365_day_ma_tx_count_sum_24h",
            "yaxis": "y",
        },
    ],
    "title": "Bitcoin Transactions",
    "x_label": "Date",
    "y1_label": "Daily Transactions",
    "y2_label": "",
    "filename": "Bitcoin_Transactions",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Hashrate Chart
chart_hashrate = {
    "x_data": "time",
    "y_data": [
        {"name": "Hash Rate", "data": "hash_rate", "yaxis": "y"},
        {"name": "Hash Rate 30 Day MA", "data": "30_day_ma_hash_rate", "yaxis": "y"},
        {"name": "Hash Rate 365 Day MA", "data": "365_day_ma_hash_rate", "yaxis": "y"},
    ],
    "title": "Bitcoin Hashrate",
    "x_label": "Date",
    "y1_label": "Network Hashrate",
    "y2_label": "",
    "filename": "Bitcoin_Hashrate",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Price Chart
chart_price = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price USD", "data": "price_close", "yaxis": "y"},
        {"name": "Bitcoin Marketcap USD", "data": "market_cap", "yaxis": "y2"},
    ],
    "title": "Bitcoin Price",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "Bitcoin Market Cap (USD)",
    "filename": "Bitcoin_Price",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Transferred Value Chart
chart_transferred_value = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {
            "name": "Transaction Volume",
            "data": "transfer_volume_sum_24h_usd",
            "yaxis": "y2",
        },
        {
            "name": "Transaction Volume 30 Day MA",
            "data": "30_day_ma_transfer_volume_sum_24h_usd",
            "yaxis": "y2",
        },
        {
            "name": "Transaction Volume 365 Day MA",
            "data": "365_day_ma_transfer_volume_sum_24h_usd",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin Transaction Volume",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Transaction Volume",
    "filename": "Bitcoin_Transaction_Value",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Miner Revenue Chart
chart_miner_revenue = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Miner Revenue", "data": "coinbase_sum_24h_usd", "yaxis": "y2"},
        {
            "name": "Miner Revenue 30 Day MA",
            "data": "30_day_ma_coinbase_sum_24h_usd",
            "yaxis": "y2",
        },
        {
            "name": "Miner Revenue 365 Day MA",
            "data": "365_day_ma_coinbase_sum_24h_usd",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin Miner Revenue",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Miner Revenue",
    "filename": "Bitcoin_Miner_Revenue",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Active Addresses Chart
chart_active_addresses = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Active Addresses", "data": "daily_active_addresses_sending", "yaxis": "y2"},
        {
            "name": "Active Addresses 30 Day MA",
            "data": "30_day_ma_daily_active_addresses_sending",
            "yaxis": "y2",
        },
        {
            "name": "Active Addresses 365 Day MA",
            "data": "365_day_ma_daily_active_addresses_sending",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin Active Addresses",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Active Addresses",
    "filename": "Bitcoin_Active_Addresses",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Transaction Fee USD Chart
chart_transaction_fee_USD = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Fees Paid (USD)", "data": "fees_sum_24h_usd", "yaxis": "y2"},
    ],
    "title": "Bitcoin Fees In USD",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Fees In US Dollars",
    "filename": "Bitcoin_Transaction_Fee",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Address Balance Count USD Chart
chart_address_balance = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": ">1 sat", "data": "addrs_over_1sat_addr_count", "yaxis": "y2"},
        {"name": ">10 sats", "data": "addrs_over_10sats_addr_count", "yaxis": "y2"},
        {"name": ">100 sats", "data": "addrs_over_100sats_addr_count", "yaxis": "y2"},
        {"name": ">1k sats", "data": "addrs_over_1k_sats_addr_count", "yaxis": "y2"},
        {"name": ">10k sats", "data": "addrs_over_10k_sats_addr_count", "yaxis": "y2"},
        {"name": ">100k sats", "data": "addrs_over_100k_sats_addr_count", "yaxis": "y2"},
        {"name": ">1M sats", "data": "addrs_over_1m_sats_addr_count", "yaxis": "y2"},
        {"name": ">10M sats", "data": "addrs_over_10m_sats_addr_count", "yaxis": "y2"},
        {"name": ">1 BTC", "data": "addrs_over_1btc_addr_count", "yaxis": "y2"},
        {"name": ">10 BTC", "data": "addrs_over_10btc_addr_count", "yaxis": "y2"},
        {"name": ">100 BTC", "data": "addrs_over_100btc_addr_count", "yaxis": "y2"},
        {"name": ">1k BTC", "data": "addrs_over_1k_btc_addr_count", "yaxis": "y2"},
        {"name": ">10k BTC", "data": "addrs_over_10k_btc_addr_count", "yaxis": "y2"},
    ],
    "title": "Address Counts Above BTC Balance Thresholds",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Address Count",
    "filename": "Bitcoin_Address_Balance",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# 1+ Year Active Supply Chart
chart_1_year_supply = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {
            "name": "1+ Year Active Supply",
            "data": "supply_pct_1_year_plus",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin 1+ Year Supply",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "1+ Year Supply Percentage",
    "filename": "Bitcoin_1_Year_Supply",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Macro Supply
macro_supply = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Liquid Supply", "data": "liquid_supply", "yaxis": "y2"},
        {"name": "Illiquid Supply", "data": "illiquid_supply", "yaxis": "y2"},
        {"name": "STH Supply", "data": "sth_supply", "yaxis": "y2"},
        {"name": "LTH Supply", "data": "lth_supply", "yaxis": "y2"},
       #{"name": "Miner Supply", "data": "SplyMiner0HopAllNtv", "yaxis": "y2"},
        #{"name": "1 Hop Miner Supply", "data": "SplyMiner1HopAllNtv", "yaxis": "y2"},
        {"name": "Daily Tx Amount", "data": "tx_count_sum_24h", "yaxis": "y2"},
        {"name": "Current Supply", "data": "supply", "yaxis": "y2"},
    ],
    "title": "Bitcoin Macro Supply",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Bitcoins Supply",
    "filename": "Bitcoin_Macro_Supply",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Thermocap Price Multiple Chart
chart_thermocap_multiple = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Thermocap Price", "data": "thermocap_price", "yaxis": "y"},
        {
            "name": "4x Thermocap Price Multiple",
            "data": "thermocap_price_multiple_4",
            "yaxis": "y",
        },
        {
            "name": "8x Thermocap Price Multiple",
            "data": "thermocap_price_multiple_8",
            "yaxis": "y",
        },
        {
            "name": "16x Thermocap Price Multiple",
            "data": "thermocap_price_multiple_16",
            "yaxis": "y",
        },
        {
            "name": "32x Thermocap Price Multiple",
            "data": "thermocap_price_multiple_32",
            "yaxis": "y",
        },
    ],
    "title": "Bitcoin Thermocap Multiple",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "",
    "filename": "Bitcoin_Thermocap_Multiples",
    "chart_type": "line",
    "filter_metric": "thermocap_multiple",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Realized Price Multiple Chart
chart_realizedcap_multiple = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "log",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Realized Price", "data": "realized_price", "yaxis": "y"},
        {"name": "STH Realized Price", "data": "sth_realized_price", "yaxis": "y"},
        {"name": "LTH Realized Price", "data": "lth_realized_price", "yaxis": "y"},
        {"name": "2x Realized Price", "data": "realizedcap_multiple_2", "yaxis": "y"},
        {"name": "3x Realized Price", "data": "realizedcap_multiple_3", "yaxis": "y"},
        {"name": "5x Realized Price", "data": "realizedcap_multiple_5", "yaxis": "y"},
        {"name": "Realized Price Multiple ", "data": "CapMVRVCur", "yaxis": "y2"},
    ],
    "title": "Bitcoin Realized Price",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "MVRV Ratio",
    "filename": "Bitcoin_Realized_Price",
    "chart_type": "line",
    #"filter_metric": "CapMVRVCur",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2011-01-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# NVT Price  Chart
chart_nvt_price = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "NVT Price 30 Day MA", "data": "30_day_ma_nvt_price", "yaxis": "y"},
        {"name": "NVT Price 365 Day MA", "data": "365_day_ma_nvt_price", "yaxis": "y"},
        # {
        #  "name": "NVT Ratio 2 Year Median",
        # "data": "nvt_price_multiple_ma",
        # "yaxis": "y2",
        # },
    ],
    "title": "Bitcoin NVT Price",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "",
    "filename": "Bitcoin_NVT_Price",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Electricity Price Chart
electricity_price = {
    "x_data": "time",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {
            "name": "Power Expense ($0.05/kWh)",
            "data": "Electricity_Cost",
            "yaxis": "y",
        },
        {
            "name": "Hayes Network Price Per BTC",
            "data": "Hayes_Network_Price_Per_BTC",
            "yaxis": "y",
        },
        {
            "name": "Hayes Price Multiple",
            "data": "Hayes_Network_Price_Multiple",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin Production Price",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Hayes Price Multiple",
    "filename": "Bitcoin_Production_Price",
    "chart_type": "line",
    "filter_start_date": "2010-07-01",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Electricity Tariff Scenarios Chart
chart_electricity_cost = {
    "x_data": "time",
    "y1_type": "log",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {
            "name": "Power Expense ($0.03/kWh)",
            "data": "Electricity_Cost_3c",
            "yaxis": "y",
        },
        {
            "name": "Power Expense ($0.04/kWh)",
            "data": "Electricity_Cost_4c",
            "yaxis": "y",
        },
        {
            "name": "Power Expense ($0.05/kWh)",
            "data": "Electricity_Cost_5c",
            "yaxis": "y",
        },
        {
            "name": "Power Expense ($0.06/kWh)",
            "data": "Electricity_Cost_6c",
            "yaxis": "y",
        },
        {
            "name": "Power Expense ($0.07/kWh)",
            "data": "Electricity_Cost_7c",
            "yaxis": "y",
        },
    ],
    "title": "Bitcoin Electricity Cost by Power Tariff",
    "x_label": "Date",
    "y1_label": "Bitcoin Price and Power Expense per BTC (USD)",
    "y2_label": "",
    "filename": "Bitcoin_Electricity_Cost",
    "chart_type": "line",
    "filter_start_date": "2011-03-01",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Power Law Model Chart
chart_power_law_model = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {
            "name": "Power Law Price",
            "data": "power_law_price",
            "yaxis": "y",
        },
        {
            "name": "BTC Price / Power Law Price",
            "data": "power_law_price_multiple",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin Power Law Model",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "BTC Price / Power Law Price",
    "filename": "Bitcoin_Power_Law_Model",
    "chart_type": "line",
    "filter_start_date": "2010-07-01",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Metcalfe Model Chart
chart_metcalfe_model = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {
            "name": "Metcalfe Value (Any Balance)",
            "data": "metcalfe_value_any_balance",
            "yaxis": "y",
        },
        {
            "name": "Metcalfe Value (0.001+ BTC)",
            "data": "metcalfe_value_0p001_btc",
            "yaxis": "y",
        },
        {
            "name": "Metcalfe Value (0.01+ BTC)",
            "data": "metcalfe_value_0p01_btc",
            "yaxis": "y",
        },
        {
            "name": "Metcalfe Value (0.1+ BTC)",
            "data": "metcalfe_value_0p1_btc",
            "yaxis": "y",
        },
        {
            "name": "BTC Price / Metcalfe Value",
            "data": "metcalfe_price_multiple",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin Metcalfe Model",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "BTC Price / Metcalfe Value",
    "filename": "Bitcoin_Metcalfe_Model",
    "chart_type": "line",
    "filter_start_date": "2010-07-01",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Hash Ribbons Chart
chart_hash_ribbons = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "log",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {
            "name": "Hash Rate 30-Day MA",
            "data": "30_day_ma_hash_rate",
            "yaxis": "y2",
        },
        {
            "name": "Hash Rate 60-Day MA",
            "data": "60_day_ma_hash_rate",
            "yaxis": "y2",
        },
    ],
    "title": "Bitcoin Hash Ribbons",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "Hash Rate (H/s)",
    "filename": "Bitcoin_Hash_Ribbons",
    "chart_type": "line",
    "filter_start_date": "2010-07-01",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Stock To Flow Chart
s2f_price = {
    "x_data": "time",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Stock-To-Flow Price", "data": "SF_Predicted_Price", "yaxis": "y"},
        {"name": "Stock-To-Flow Multiple", "data": "SF_Multiple", "yaxis": "y2"},
        
    ],
    "title": "Bitcoin Stock To Flow Price",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Stock To Flow Multiple",
    "filename": "Bitcoin_S2F_Price",
    "chart_type": "line",
    "filter_start_date": "2010-07-01",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# NUPL Chart
chart_NUPL = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Net Unrealized Profit Loss", "data": "nupl", "yaxis": "y2"},
    ],
    "title": "Bitcoin Net Unrealized Profit Loss Ratio",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "NUPL Ratio",
    "filename": "Bitcoin_NUPL",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Price Chart
chart_price_ma = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "7 Day MA", "data": "7_day_ma_price_close", "yaxis": "y"},
        {"name": "50 Day MA", "data": "50_day_ma_price_close", "yaxis": "y"},
        {"name": "200 Day MA", "data": "200_day_ma_price_close", "yaxis": "y"},
        {"name": "200 Week MA", "data": "200_week_ma_price_close", "yaxis": "y"},
        {"name": "200 Day MA Multiple", "data": "200_day_multiple", "yaxis": "y2"},
    ],
    "title": "Bitcoin Price Moving Averages",
    "filter_metric": "price_close",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "200 Day Moving Average Multiple",
    "filename": "Bitcoin_Price_Chart_MA",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2011-01-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin YOY Retrun Comparison
yoy_return = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin YOY Return", "data": "price_close_YOY_change", "yaxis": "y2"},
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
    ],
    "title": "Year Over Year Return",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "Year Over Year Return (Percentage)",
    "filter_start_date": "2015-01-01",
    "filter_metric": "price_close_YOY_change",
    "filename": "Bitcoin_YOY_Return_Comparison",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
}

# Bitcoin CAGR Comparison
cagr_overview = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Bitcoin 4 Year CAGR", "data": "price_close_4_Year_CAGR", "yaxis": "y2"},
    ],
    "title": "4 Year Compound Annual Growth Rate",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "4 Year CAGR (Percentage)",
    "filter_start_date": "2015-01-01",
    "filter_metric": "price_close_4_Year_CAGR",
    "filename": "Bitcoin_CAGR",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
}

# Hashrate Chart
chart_sats_per_dollar = {
    "x_data": "time",
    "y_data": [
        {"name": "Satoshis Per Dollar", "data": "sat_per_dollar", "yaxis": "y1"},
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y2"},
    ],
    "title": "Satoshis Per Dollar",
    "x_label": "Date",
    "y1_label": "Satoshis Per Dollar | Amount Of Bitcoin You Can Purchase Per $1",
    "y2_label": "1 Full Bitcoin Price",
    "filename": "Bitcoin_Sats_Per_Dollar",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin m0
chart_m0 = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "United States", "data": "United_States_btc_price", "yaxis": "y"},
        {"name": "China", "data": "China_btc_price", "yaxis": "y"},
        {"name": "Eurozone", "data": "Eurozone_btc_price", "yaxis": "y"},
        {"name": "Japan", "data": "Japan_btc_price", "yaxis": "y"},
        {"name": "United Kingdom", "data": "United_Kingdom_btc_price", "yaxis": "y"},
        {"name": "Switzerland", "data": "Switzerland_btc_price", "yaxis": "y"},
        {"name": "India", "data": "India_btc_price", "yaxis": "y"},
        {"name": "Australia", "data": "Australia_btc_price", "yaxis": "y"},
        {"name": "Russia", "data": "Russia_btc_price", "yaxis": "y"},
    ],
    "title": "Bitcoin Price VS M0 Money Supply",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_M0",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Equity market-cap fields published by the local Report Library. Keep the broad
# equities chart tied to this single ordered catalog so newly grouped RV charts
# cannot drift onto different labels or column names.
EQUITY_RELATIVE_VALUE_SERIES = {
    "AAPL": ("Apple", "AAPL_mc_btc_price"),
    "MSFT": ("Microsoft", "MSFT_mc_btc_price"),
    "GOOGL": ("Alphabet", "GOOGL_mc_btc_price"),
    "AMZN": ("Amazon", "AMZN_mc_btc_price"),
    "NVDA": ("NVIDIA", "NVDA_mc_btc_price"),
    "AVGO": ("Broadcom", "AVGO_mc_btc_price"),
    "TSLA": ("Tesla", "TSLA_mc_btc_price"),
    "LLY": ("Eli Lilly", "LLY_mc_btc_price"),
    "MU": ("Micron", "MU_mc_btc_price"),
    "META": ("Meta", "META_mc_btc_price"),
    "BRK-A": ("Berkshire Hathaway A", "BRK-A_mc_btc_price"),
    "BRK-B": ("Berkshire Hathaway B", "BRK-B_mc_btc_price"),
    "TSM": ("TSMC", "TSM_mc_btc_price"),
    "SPCX": ("SpaceX", "SPCX_mc_btc_price"),
    "2222.SR": ("Saudi Aramco", "2222.SR_mc_btc_price"),
    "005930.KS": ("Samsung Electronics", "005930.KS_mc_btc_price"),
    "V": ("Visa", "V_mc_btc_price"),
    "JPM": ("JPMorgan", "JPM_mc_btc_price"),
    "PYPL": ("PayPal", "PYPL_mc_btc_price"),
    "GS": ("Goldman Sachs", "GS_mc_btc_price"),
    "COIN": ("Coinbase", "COIN_mc_btc_price"),
    "XYZ": ("Block", "XYZ_mc_btc_price"),
    "MSTR": ("Strategy", "MSTR_mc_btc_price"),
    "MARA": ("MARA", "MARA_mc_btc_price"),
    "RIOT": ("Riot", "RIOT_mc_btc_price"),
}


def _equity_relative_value_traces(*tickers):
    """Build primary-axis traces for selected equity market-cap BTC prices."""
    return [
        {
            "name": EQUITY_RELATIVE_VALUE_SERIES[ticker][0],
            "data": EQUITY_RELATIVE_VALUE_SERIES[ticker][1],
            "yaxis": "y",
        }
        for ticker in tickers
    ]


# Equities Market Cap Chart
chart_equities = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        *_equity_relative_value_traces(*EQUITY_RELATIVE_VALUE_SERIES),
    ],
    "title": "Bitcoin Price vs Mega Equity Market Caps",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_Equities",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
    "height": 900,
    "bottom_margin": 380,
    "legend_y": -0.12,
    "legend_yanchor": "top",
    "legend_font_size": 12,
    "controls_y": -0.72,
    "source_y": -0.84,
}

# Gold Market Cap Chart
chart_gold = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Gold Marketcap", "data": "gold_marketcap_btc_price", "yaxis": "y"},
        {
            "name": "Silver Marketcap",
            "data": "silver_marketcap_btc_price",
            "yaxis": "y",
        },
        {
            "name": "Gold Jewellery",
            "data": "gold_jewellery_marketcap_btc_price",
            "yaxis": "y",
        },
        {
            "name": "Gold Private Investment",
            "data": "gold_private_investment_marketcap_btc_price",
            "yaxis": "y",
        },
        {
            "name": "Gold Country Holdings",
            "data": "gold_official_country_holdings_marketcap_btc_price",
            "yaxis": "y",
        },
        {
            "name": "Gold Other / Industrial",
            "data": "gold_other_marketcap_btc_price",
            "yaxis": "y",
        },
    ],
    "title": "Bitcoin Price VS Gold Market Cap",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_Gold",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Promo Chart
chart_promo = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Realized Price", "data": "realized_price", "yaxis": "y"},
        {
            "name": "Thermocap Multiple 32x",
            "data": "thermocap_price_multiple_32",
            "yaxis": "y",
        },
        {"name": "200 Week MA", "data": "200_week_ma_price_close", "yaxis": "y"},
        {"name": "Hash Rate 30 Day MA", "data": "30_day_ma_hash_rate", "yaxis": "y2"},
        {"name": "Hash Rate 365 Day MA", "data": "365_day_ma_hash_rate", "yaxis": "y2"},
    ],
    "title": "Bitcoin 101",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "hash_rate",
    "filename": "Bitcoin_Promo",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Relative Valuation
chart_rv_metals = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Silver", "data": "silver_marketcap_btc_price", "yaxis": "y"},
        {
            "name": "Gold Country Holdings",
            "data": "gold_official_country_holdings_marketcap_btc_price",
            "yaxis": "y",
        },
        {
            "name": "Gold Private Investment",
            "data": "gold_private_investment_marketcap_btc_price",
            "yaxis": "y",
        },
        {"name": "Total Gold Market", "data": "gold_marketcap_btc_price", "yaxis": "y"},
    ],
    "title": "Bitcoin Price Relative Valuation - Metals",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_RV_metals",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Relative Valuation
chart_rv_stocks = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        *_equity_relative_value_traces("META", "AMZN", "GOOGL", "MSFT", "AAPL"),
    ],
    "title": "Bitcoin Price Relative Valuation - Stocks",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_RV_stocks",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Relative Valuation - Semiconductors
chart_rv_semiconductors = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        *_equity_relative_value_traces("NVDA", "AVGO", "TSM", "005930.KS", "MU"),
    ],
    "title": "Bitcoin Price Relative Valuation - Semiconductors",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_RV_Semiconductors",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2015-01-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Relative Valuation - Financials and Payments
chart_rv_financials = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        *_equity_relative_value_traces("BRK-B", "JPM", "GS", "V", "PYPL", "XYZ"),
    ],
    "title": "Bitcoin Price Relative Valuation - Financials and Payments",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_RV_Financials",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2015-01-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Relative Valuation - Cross-Sector Leaders
chart_rv_sector_leaders = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        *_equity_relative_value_traces("TSLA", "LLY", "2222.SR", "SPCX"),
    ],
    "title": "Bitcoin Price Relative Valuation - Cross-Sector Leaders",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_RV_Sector_Leaders",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2015-01-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Relative Valuation
chart_rv_m0 = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "United Kingdom", "data": "United_Kingdom_btc_price", "yaxis": "y"},
        {"name": "Japan", "data": "Japan_btc_price", "yaxis": "y"},
        {"name": "China", "data": "China_btc_price", "yaxis": "y"},
        {"name": "United States", "data": "United_States_btc_price", "yaxis": "y"},
        {"name": "EU", "data": "Eurozone_btc_price", "yaxis": "y"},
    ],
    "title": "Bitcoin Price Relative Valuation - M0",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_RV_M0",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin On-Chain
chart_on_chain = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "200 Week MA", "data": "200_week_ma_price_close", "yaxis": "y"},

        {
            "name": "Hayes Network Price Per BTC",
            "data": "Hayes_Network_Price_Per_BTC",
            "yaxis": "y",
        },
        {"name": "STH Realized Price", "data": "sth_realized_price", "yaxis": "y"},
        {"name": "LTH Realized Price", "data": "lth_realized_price", "yaxis": "y"},
        {"name": "Realized Price", "data": "realized_price", "yaxis": "y"},
        {"name": "3x Realized Price", "data": "realizedcap_multiple_3", "yaxis": "y"},
    ],
    "title": "Bitcoin Price On-Chain Value",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_On_Chain",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Promo Chart
chart_hashrate_price = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Hash Rate", "data": "hash_rate", "yaxis": "y2"},
        {"name": "Hash Rate 30 Day MA", "data": "30_day_ma_hash_rate", "yaxis": "y2"},
        {"name": "Hash Rate 365 Day MA", "data": "365_day_ma_hash_rate", "yaxis": "y2"},
    ],
    "title": "Bitcoin Price & Hashrate",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "hash_rate",
    "filename": "Bitcoin_Hashrate_Price",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Supply Age by UTXO Age Chart
chart_supply_age = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Supply < 1 Month", "data": "utxos_under_1m_old_supply", "yaxis": "y2"},
        {"name": "Supply < 3 Months", "data": "utxos_under_3m_old_supply", "yaxis": "y2"},
        {"name": "Supply < 6 Months", "data": "utxos_under_6m_old_supply", "yaxis": "y2"},
        {"name": "Supply < 1 Year", "data": "utxos_under_1y_old_supply", "yaxis": "y2"},
        {"name": "Supply < 2 Years", "data": "utxos_under_2y_old_supply", "yaxis": "y2"},
        {"name": "Supply < 3 Years", "data": "utxos_under_3y_old_supply", "yaxis": "y2"},
        {"name": "Supply < 4 Years", "data": "utxos_under_4y_old_supply", "yaxis": "y2"},
        {"name": "Supply < 5 Years", "data": "utxos_under_5y_old_supply", "yaxis": "y2"},
        {"name": "Supply < 10 Years", "data": "utxos_under_10y_old_supply", "yaxis": "y2"},
        {"name": "Current Supply", "data": "supply", "yaxis": "y2"},
    ],
    "title": "Supply Age Distribution",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Supply (BTC)",
    "filename": "Bitcoin_Supply_Age",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin CAGR Comparison
cagr_comparison = {
    "x_data": "time",
    "y1_type": "linear",
    "y_data": [
        {"name": "Bitcoin", "data": "price_close_4_Year_CAGR", "yaxis": "y"},
        {
            "name": "S&P 500 Index ETF",
            "data": "SPY_close_4_Year_CAGR",
            "yaxis": "y",
        },
        {
            "name": "Nasdaq-100 ETF",
            "data": "QQQ_close_4_Year_CAGR",
            "yaxis": "y",
        },
        {
            "name": "Technology Sector ETF",
            "data": "XLK_close_4_Year_CAGR",
            "yaxis": "y",
        },
        {
            "name": "Financials Sector ETF",
            "data": "XLF_close_4_Year_CAGR",
            "yaxis": "y",
        },
        {"name": "Gold ETF", "data": "GLD_close_4_Year_CAGR", "yaxis": "y"},
        {
            "name": "Aggregate Bond ETF",
            "data": "AGG_close_4_Year_CAGR",
            "yaxis": "y",
        },
        {
            "name": "US Dollar Index",
            "data": "DX-Y.NYB_close_4_Year_CAGR",
            "yaxis": "y",
        },
        {
            "name": "Bitcoin Miners ETF",
            "data": "WGMI_close_4_Year_CAGR",
            "yaxis": "y",
        },
    ],
    "title": "4 Year Compound Annual Growth Rate Comparison",
    "x_label": "Date",
    "y1_label": "4 Year CAGR (Percentage)",
    "y2_label": "",
    "filename": "Bitcoin_CAGR_Comparison",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2015-05-01",
}

# Bitcoin MTD Return Comparison
mtd_return = {
    "x_data": "time",
    "y1_type": "linear",
    "y_data": [
        {"name": "Bitcoin", "data": "price_close_MTD_change", "yaxis": "y"},
        {
            "name": "S&P 500 Index ETF",
            "data": "SPY_close_MTD_change",
            "yaxis": "y",
        },
        {
            "name": "Nasdaq-100 ETF",
            "data": "QQQ_close_MTD_change",
            "yaxis": "y",
        },
        {
            "name": "Technology Sector ETF",
            "data": "XLK_close_MTD_change",
            "yaxis": "y",
        },
        {
            "name": "Financials Sector ETF",
            "data": "XLF_close_MTD_change",
            "yaxis": "y",
        },
        {"name": "Gold ETF", "data": "GLD_close_MTD_change", "yaxis": "y"},
        {
            "name": "Aggregate Bond ETF",
            "data": "AGG_close_MTD_change",
            "yaxis": "y",
        },
        {
            "name": "US Dollar Index",
            "data": "DX-Y.NYB_close_MTD_change",
            "yaxis": "y",
        },
        {
            "name": "Bitcoin Miners ETF",
            "data": "WGMI_close_MTD_change",
            "yaxis": "y",
        },
    ],
    "title": f"Month To Date Return Comparison - {current_month_year}",
    "x_label": "Date",
    "y1_label": "Month To Date Return (Percentage)",
    "y2_label": "",
    "filename": "Bitcoin_MTD_Return_Comparison",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": first_day_of_month,  # Start of the current month
}

# Shortened Year To Date Return Comparison
ytd_return = {
    "x_data": "time",
    "y1_type": "linear",
    "y_data": [
        {"name": "Bitcoin", "data": "price_close_YTD_change", "yaxis": "y"},
        {
            "name": "S&P 500 Index ETF",
            "data": "SPY_close_YTD_change",
            "yaxis": "y",
        },
        {
            "name": "Nasdaq-100 ETF",
            "data": "QQQ_close_YTD_change",
            "yaxis": "y",
        },
        {
            "name": "Technology Sector ETF",
            "data": "XLK_close_YTD_change",
            "yaxis": "y",
        },
        {
            "name": "Financials Sector ETF",
            "data": "XLF_close_YTD_change",
            "yaxis": "y",
        },
        {"name": "Gold ETF", "data": "GLD_close_YTD_change", "yaxis": "y"},
        {
            "name": "Aggregate Bond ETF",
            "data": "AGG_close_YTD_change",
            "yaxis": "y",
        },
        {
            "name": "US Dollar Index",
            "data": "DX-Y.NYB_close_YTD_change",
            "yaxis": "y",
        },
        {
            "name": "Bitcoin Miners ETF",
            "data": "WGMI_close_YTD_change",
            "yaxis": "y",
        },
    ],
    "title": f"Year To Date Return ({current_year})",
    "x_label": "Date",
    "y1_label": "Year To Date Return (Percentage)",
    "y2_label": "",
    "filename": "Bitcoin_YTD_Return_Comparison",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": f"{current_year}-01-01",
    "filter_metric": "time",
}

# Full list Year To Date Return Comparison
ytd_return_full = {
    "x_data": "time",
    "y1_type": "linear",
    "y_data": [
        {"name": "BTC", "data": "price_close_YTD_change", "yaxis": "y"},
        {"name": "SPY", "data": "SPY_close_YTD_change", "yaxis": "y"},
        {"name": "QQQ", "data": "QQQ_close_YTD_change", "yaxis": "y"},
        {"name": "VTI", "data": "VTI_close_YTD_change", "yaxis": "y"},
        {"name": "VXUS", "data": "VXUS_close_YTD_change", "yaxis": "y"},
        {"name": "XLK", "data": "XLK_close_YTD_change", "yaxis": "y"},
        {"name": "XLF", "data": "XLF_close_YTD_change", "yaxis": "y"},
        {"name": "XLE", "data": "XLE_close_YTD_change", "yaxis": "y"},
        {"name": "XLRE", "data": "XLRE_close_YTD_change", "yaxis": "y"},
        {"name": "DXY", "data": "DX-Y.NYB_close_YTD_change", "yaxis": "y"},
        {"name": "GLD", "data": "GLD_close_YTD_change", "yaxis": "y"},
        {"name": "AGG", "data": "AGG_close_YTD_change", "yaxis": "y"},
        {"name": "SPGSCI", "data": "^SPGSCI_close_YTD_change", "yaxis": "y"},
        {"name": "MSTR", "data": "MSTR_close_YTD_change", "yaxis": "y"},
        {"name": "XYZ", "data": "XYZ_close_YTD_change", "yaxis": "y"},
        {"name": "COIN", "data": "COIN_close_YTD_change", "yaxis": "y"},
        {"name": "WGMI", "data": "WGMI_close_YTD_change", "yaxis": "y"},
    ],
    "title": f"Year To Date Return ({current_year})",
    "x_label": "Date",
    "y1_label": "Year To Date Return (Percentage)",
    "y2_label": "",
    "filename": "Bitcoin_YTD_Return_Comparison_full",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": f"{current_year}-01-01",
    "filter_metric": "time",
}

# ATH Drawdown Chart
chart_drawdowns = {
    "x_data": "days_since_ath",
    "value_col": "drawdown_pct",
    "group_col": "Cycle",
    "y1_type": "linear",
    "y_data": [
        {"name": "Drawdown Cycle 1", "group": "Drawdown Cycle 1"},
        {"name": "Drawdown Cycle 2", "group": "Drawdown Cycle 2"},
        {"name": "Drawdown Cycle 3", "group": "Drawdown Cycle 3"},
        {"name": "Drawdown Cycle 4", "group": "Drawdown Cycle 4"},
        {"name": "Drawdown Cycle 5", "group": "Drawdown Cycle 5"},
    ],
    "title": "Bitcoin Drawdowns From ATH",
    "x_label": "Days Since ATH",
    "y1_label": "Drawdown (%)",
    "filename": "Bitcoin_ATH_Drawdown",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "hovertemplate": "Drawdown %{y:,.2f}%<extra>%{fullData.name}</extra>",
    "y_tickformat": ",.2f",
}

# Cycle Low Chart
chart_cycle_lows = {
    "x_data": "days_since_cycle_low",
    "value_col": "index_value",
    "group_col": "Cycle",
    "y1_type": "log",
    "price_scale": {
        "anchor_date": "2026-02-06",
        "price_col": "price_close",
    },
    "y_data": [
        {"name": "Market Cycle 1", "group": "Market Cycle 1"},
        {"name": "Market Cycle 2", "group": "Market Cycle 2"},
        {"name": "Market Cycle 3", "group": "Market Cycle 3"},
        {"name": "Market Cycle 4", "group": "Market Cycle 4"},
        {"name": "Market Cycle 5", "group": "Market Cycle 5"},
        {"name": "Market Cycle 6", "group": "Market Cycle 6"},
    ],
    "title": "Bitcoin Price Performance Since Cycle Low",
    "x_label": "Days Since Cycle Low",
    "y1_label": "Bitcoin Price Indexed to Current Cycle Low ($)",
    "filename": "Bitcoin_Cycle_Low",
    "data_source": "Data Source: Bitview",
    "hovertemplate": "$%{y:,.0f}<extra>%{fullData.name}</extra>",
    "y_tickformat": "$,.0f",
}

# Halving Performane Chart
chart_halvings = {
    "x_data": "days_since_halving",
    "value_col": "index_value",
    "group_col": "Era",
    "y1_type": "log",
    "y_data": [
        {"name": "2012–16",      "group": "2nd Era"},
        {"name": "2016–20",      "group": "3rd Era"},
        {"name": "2020–24",      "group": "4th Era"},
        {"name": "2024+",        "group": "5th Era"},
    ],
    "title": "Bitcoin Index Performance Since Halving",
    "x_label": "Days Since Halving",
    "y1_label": "Cycle Index Value (1.0 = halving price)",
    "filename": "Bitcoin_Halving_Cycle",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "hovertemplate": "Index %{y:,.2f}×<extra>%{fullData.name}</extra>",
    "y_tickformat": "~g",
}

# Bitcoin Relative Valuation - Composite
chart_rv = {
    "x_data": "time",
    "y_data": [
        {"name": "Bitcoin", "data": "price_close", "yaxis": "y"},
        {"name": "Total Silver Market", "data": "silver_marketcap_btc_price", "yaxis": "y"},
        {"name": "UK M0", "data": "United_Kingdom_btc_price", "yaxis": "y"},
        {"name": "Meta", "data": "META_mc_btc_price", "yaxis": "y"},
        {"name": "Amazon", "data": "AMZN_mc_btc_price", "yaxis": "y"},
        {
            "name": "Gold Country Holdings",
            "data": "gold_official_country_holdings_marketcap_btc_price",
            "yaxis": "y",
        },
        {"name": "NVIDIA", "data": "NVDA_mc_btc_price", "yaxis": "y"},
        {
            "name": "Gold Private Investment",
            "data": "gold_private_investment_marketcap_btc_price",
            "yaxis": "y",
        },
        {"name": "Apple", "data": "AAPL_mc_btc_price", "yaxis": "y"},
        {"name": "US M0", "data": "United_States_btc_price", "yaxis": "y"},
        {"name": "Total Gold Market", "data": "gold_marketcap_btc_price", "yaxis": "y"},
    ],
    "title": "Bitcoin Price Relative Valuation",
    "x_label": "Date",
    "y1_label": "Bitcoin Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_RV",
    "chart_type": "line",
    "data_source": "Data Source: Bitview",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Adjusted Bitcoin Days Destroyed Chart 
chart_adjusted_bdd = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Adjusted BDD", "data": "adjusted_bdd", "yaxis": "y2"},
        {"name": "Adjusted BDD Mean", "data": "adjusted_bdd_mean", "yaxis": "y2"},
    ],
    "title": "Adjusted Bitcoin Days Destroyed (BDD / Circulating Supply)",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Adjusted BDD",
    "filename": "Bitcoin_Adjusted_BDD",
    "chart_type": "line",
    "data_source": "Data Source: BRK (Calculated)",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Puell Multiple Chart
chart_puell_multiple = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Puell Multiple", "data": "puell_multiple", "yaxis": "y2"},
    ],
    "title": "Bitcoin Puell Multiple",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Puell Multiple",
    "filename": "Bitcoin_Puell_Multiple",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2011-01-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# HODL Bank & Reserve Risk Chart
chart_hodl_bank = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "log",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "VOCD", "data": "vocd", "yaxis": "y"},
        {"name": "MVOCD", "data": "mvocd", "yaxis": "y"},
        {"name": "HODL Bank", "data": "hodl_bank_calc", "yaxis": "y"},
        {"name": "Reserve Risk", "data": "reserve_risk_calc", "yaxis": "y2"},
    ],
    "title": "Bitcoin HODL Bank & Reserve Risk",
    "x_label": "Date",
    "y1_label": "USD Value",
    "y2_label": "Reserve Risk",
    "filename": "Bitcoin_HODL_Bank",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Delta Cap Chart (Price Format)
chart_delta_cap = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "log",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Realized Price", "data": "realized_price", "yaxis": "y"},
        {"name": "Average Cap Price", "data": "average_cap_price", "yaxis": "y"},
        {"name": "Delta Cap Price", "data": "delta_cap_price", "yaxis": "y"},
    ],
    "title": "Bitcoin Delta Cap",
    "x_label": "Date",
    "y1_label": "Price (USD)",
    "y2_label": "",
    "filename": "Bitcoin_Delta_Cap",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Bitcoin Volatility Chart
chart_volatility = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "30-Day Volatility", "data": "VtyDayRet30d", "yaxis": "y2"},
        {"name": "180-Day Volatility", "data": "VtyDayRet180d", "yaxis": "y2"},
    ],
    "title": "Bitcoin Volatility",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Annualized Volatility",
    "filename": "Bitcoin_Volatility",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# SOPR (Spent Output Profit Ratio) Chart
chart_sopr = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "SOPR", "data": "sopr_24h", "yaxis": "y2"},
    ],
    "title": "Bitcoin SOPR (Spent Output Profit Ratio)",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "SOPR",
    "filename": "Bitcoin_SOPR",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2012-01-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Supply in Profit/Loss Chart (Percentage)
chart_supply_profit_loss = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "linear",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Supply in Profit %", "data": "supply_in_profit_pct", "yaxis": "y2"},
        {"name": "Supply in Loss %", "data": "supply_in_loss_pct", "yaxis": "y2"},
    ],
    "title": "Bitcoin Supply in Profit vs Loss",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "% of Supply",
    "filename": "Bitcoin_Supply_Profit_Loss",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Hash Price Chart
chart_hash_price = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "log",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Hash Price ($/TH/s)", "data": "hash_price_ths", "yaxis": "y2"},
    ],
    "title": "Bitcoin Hash Price",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Hash Price ($/TH/s/day)",
    "filename": "Bitcoin_Hash_Price",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# Difficulty Chart
chart_difficulty = {
    "x_data": "time",
    "y1_type": "log",
    "y2_type": "log",
    "y_data": [
        {"name": "Bitcoin Price", "data": "price_close", "yaxis": "y"},
        {"name": "Difficulty", "data": "difficulty", "yaxis": "y2"},
    ],
    "title": "Bitcoin Network Difficulty",
    "x_label": "Date",
    "y1_label": "Bitcoin Price",
    "y2_label": "Difficulty",
    "filename": "Bitcoin_Difficulty",
    "chart_type": "line",
    "data_source": "Data Source: BRK",
    "filter_start_date": "2010-07-01",
    "events": BITCOIN_HISTORICAL_EVENTS,
}

# List Of All Chart Templates
chart_templates = [
    # === PRICE FUNDAMENTALS ===
    chart_price,
    chart_price_ma,
    chart_sats_per_dollar,
    chart_volatility,
    # === SUPPLY METRICS ===
    chart_supply,
    macro_supply,
    chart_1_year_supply,
    chart_supply_age,
    # === NETWORK ACTIVITY ===
    chart_transactions,
    chart_transaction_fee_USD,
    chart_transferred_value,
    chart_active_addresses,
    chart_address_balance,
    # === MINING & SECURITY ===
    chart_hashrate,
    chart_hashrate_price,
    chart_hash_ribbons,
    chart_difficulty,
    chart_hash_price,
    chart_miner_revenue,
    chart_puell_multiple,
    # === ON-CHAIN VALUATION ===
    chart_thermocap_multiple,
    chart_realizedcap_multiple,
    chart_delta_cap,
    chart_nvt_price,
    chart_NUPL,
    # === HOLDER BEHAVIOR ===
    chart_adjusted_bdd,
    chart_hodl_bank,
    chart_sopr,
    chart_supply_profit_loss,
    # === PRICE MODELS ===
    electricity_price,
    chart_electricity_cost,
    chart_power_law_model,
    chart_metcalfe_model,
    s2f_price,
    # === ASSET COMPARISONS ===
    chart_gold,
    chart_rv_metals,
    chart_equities,
    chart_rv_stocks,
    chart_rv_semiconductors,
    chart_rv_financials,
    chart_rv_sector_leaders,
    chart_m0,
    chart_rv_m0,
    chart_on_chain,
    chart_rv,
    # === RETURNS & PERFORMANCE ===
    yoy_return,
    cagr_overview,
    cagr_comparison,
    mtd_return,
    ytd_return,
    ytd_return_full,
    chart_promo,
]
