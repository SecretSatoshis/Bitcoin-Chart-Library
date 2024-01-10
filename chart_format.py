import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd

# Create Line Chart Functoin
def create_line_chart(chart_template, selected_metrics):
  # Check for the presence of filter_start_date in the template
  if 'filter_start_date' in chart_template and 'filter_metric' in chart_template:
      filter_metric = chart_template['filter_metric']
      start_date = pd.to_datetime(chart_template['filter_start_date'])

      # Check if filter_end_date is also specified
      if 'filter_end_date' in chart_template:
          end_date = pd.to_datetime(chart_template['filter_end_date'])
      else:
          end_date = selected_metrics.index.max()  # Use the maximum date available in the data

      # Apply the date filter only to the specified metric
      if filter_metric in selected_metrics.columns:
          selected_metrics = selected_metrics[(selected_metrics.index >= start_date) & (selected_metrics.index <= end_date) & selected_metrics[filter_metric].notnull()]
  x = selected_metrics.index
  y_data = chart_template['y_data']
  title = chart_template['title']
  x_label = chart_template['x_label']
  y1_label = chart_template['y1_label']
  y2_label = chart_template['y2_label']
  filename = chart_template['filename']
  y1_type = chart_template.get('y1_type', 'log')
  y2_type = chart_template.get('y2_type', 'linear')
  data_source_text = chart_template['data_source']

  # Define Colors For Line Charts Items
  colors = [
    '#7149C6', '#0079FF', '#FF0060', '#22A699', '#8c564b', '#e377c2',
    '#7f7f7f', '#bcbd22', '#17becf'
  ]

  # Create an empty Plotly Figure object
  fig = go.Figure()

  # Add line traces to the figure for each item in y_data
  for i, y_item in enumerate(y_data):
    line_color = colors[
      i % len(colors)] if y_item['data'] != 'PriceUSD' else '#FF9900'
    fig.add_trace(
      go.Scatter(x=x,
                 y=selected_metrics[y_item['data']],
                 mode='lines',
                 name=y_item['name'],
                 line=dict(color=line_color),
                 yaxis=y_item['yaxis'],
                 hovertemplate='%{y:,.2f}<extra></extra>'))

  # Update the layout of the figure with various styling options
  fig.update_layout(
    title=dict(text=title, x=0.5, xanchor='center', y=0.98),
    xaxis_title=x_label,
    yaxis_title=y1_label,
    yaxis=dict(showgrid=False, type=y1_type, autorange=True),
    yaxis2=dict(title=y2_label,
                overlaying='y',
                side='right',
                showgrid=False,
                type=y2_type,
                autorange=True),
    plot_bgcolor='rgba(255, 255, 255, 1)',
    xaxis=dict(showgrid=False,
               tickformat='%B-%d-%Y',
               rangeslider_visible=False,
               rangeselector=dict(buttons=list([
                 dict(count=1, label="1m", step="month", stepmode="backward"),
                 dict(count=6, label="6m", step="month", stepmode="backward"),
                 dict(count=1, label="YTD", step="year", stepmode="todate"),
                 dict(count=1, label="1y", step="year", stepmode="backward"),
                 dict(count=2, label="2y", step="year", stepmode="backward"),
                 dict(count=3, label="3y", step="year", stepmode="backward"),
                 dict(count=5, label="5y", step="year", stepmode="backward"),
                 dict(count=10, label="10y", step="year", stepmode="backward"),
                 dict(step="all")
               ])),
               autorange=True),
    hovermode='x',
    autosize=True,
    legend=dict(orientation='h',
                yanchor='bottom',
                y=-0.15,
                xanchor='center',
                x=0.5),
    template='plotly_white',
    updatemenus=[
      go.layout.Updatemenu(buttons=list([
        dict(label="Y1-axis: Linear",
             method="relayout",
             args=["yaxis.type", "linear"]),
        dict(label="Y1-axis: Log",
             method="relayout",
             args=["yaxis.type", "log"]),
        dict(label="Y2-axis: Linear",
             method="relayout",
             args=["yaxis2.type", "linear"]),
        dict(label="Y2-axis: Log",
             method="relayout",
             args=["yaxis2.type", "log"])
      ]),
                           showactive=False,
                           type="buttons",
                           direction="right",
                           x=-0.1,
                           xanchor="left",
                           y=-0.15,
                           yanchor="top")
    ],
    width=1400,
    height=700,
    margin=dict(l=0, r=0, b=0, t=100, pad=2),
    font=dict(family="PT Sans Narrow", size=14, color="black"))

  fig.update_layout(yaxis=dict(tickformat=",.2f"))

  # Add event annotations and lines to the figure
  if 'events' in chart_template:
    for event in chart_template['events']:
      event_dates = pd.to_datetime(event['dates'])
      orientation = event.get('orientation', 'v')
      for date in event_dates:
        if orientation == 'v':  # vertical line
          fig.add_shape(type="line",
                        xref="x",
                        yref="paper",
                        x0=date.strftime("%Y-%m-%d"),
                        y0=0,
                        x1=date.strftime("%Y-%m-%d"),
                        y1=1,
                        line=dict(color="black", width=1, dash="dash"))
        elif orientation == 'h':  # horizontal line
          y_value = event.get('y_value', None)
          if y_value:  # make sure y_value is provided and is not zero
            fig.add_shape(type="line",
                          xref="paper",
                          yref="y",
                          x0=0,
                          y0=y_value,
                          x1=1,
                          y1=y_value,
                          line=dict(color="black", width=1, dash="dash"))
        fig.add_annotation(
          x=date.strftime("%Y-%m-%d"),
          y=5,  # Place the annotation at the bottom of the y-axis
          text=event['name'],
          showarrow=False,
          font=dict(color="black"),
          xanchor="right",
          yanchor=
          "top"  # Align the top edge of the annotation with the y position
        )

  # Add watermark annotation to the figure
  fig.add_annotation(
    xref="paper",
    yref="paper",
    x=0.5,
    y=0.5,
    text="SecretSatoshis.com",
    showarrow=False,
    font=dict(size=50, color="rgba(128, 128, 128, 0.5)"),
    align="center",
  )
  # Add logo image as an annotation
  fig.add_layout_image(
    dict(
      source=
      "https://secretsatoshis.github.io/Bitcoin-Chart-Library/Secret_Satoshis_Logo.png",  # Ensure this path is correct
      x=0.0,
      y=1.2,
      sizex=0.1,
      sizey=0.1,  # Adjust size of the logo as needed
      xanchor="left",
      yanchor="top"))
  fig.add_annotation(
    text=data_source_text,  # Text from the chart template
    xref="paper",
    yref="paper",
    x=1,
    y=-0.2,  # Position at the bottom right
    xanchor="right",
    yanchor="bottom",
    showarrow=False,
    font=dict(family="Arial", size=12, color="#666"),
    align="right",
  )

  # Save the chart as an HTML file
  filepath = 'Charts/' + filename + '.html'
  pio.write_html(fig, file=filepath, auto_open=False)

  # Return the figure
  return fig

# Create Days Since Chart Function
def create_days_since_chart(drawdown_data, chart_template, filename='chart.html'):
  colors = [
    '#7149C6', '#0079FF', '#FF0060', '#22A699', '#8c564b', '#e377c2',
    '#7f7f7f', '#bcbd22', '#17becf'
  ]

  fig = go.Figure()

  # Adding traces
  for i, y_data in enumerate(chart_template['y_data']):
    line_color = colors[
      i % len(colors)] if y_data['data'] != 'PriceUSD' else '#FF9900'
    fig.add_trace(
      go.Scatter(x=drawdown_data[chart_template['x_data']],
                 y=drawdown_data[y_data['data']],
                 mode='lines',
                 name=y_data['name'],
                 line=dict(color=line_color),
                 yaxis=y_data['yaxis']))

  # Update layout
  fig.update_layout(
    title=dict(text=chart_template['title'], x=0.5, xanchor='center', y=1),
    xaxis_title=chart_template['x_label'],
    yaxis_title=chart_template['y1_label'],
    yaxis2=dict(title=chart_template['y2_label'],
                overlaying='y',
                side='right',
                showgrid=False),
    plot_bgcolor='rgba(255, 255, 255, 1)',
    yaxis=dict(showgrid=False, type='log'),
    hovermode='x unified',
    autosize=True,
    legend=dict(orientation='h',
                yanchor='bottom',
                y=-0.15,
                xanchor='center',
                x=0.5),
    template='plotly_white',
    updatemenus=[
      go.layout.Updatemenu(buttons=list([
        dict(label="Y1-axis: Linear",
             method="relayout",
             args=["yaxis.type", "linear"]),
        dict(label="Y1-axis: Log",
             method="relayout",
             args=["yaxis.type", "log"])
      ]),
                           showactive=False,
                           type="buttons",
                           direction="right",
                           x=-0.1,
                           xanchor="left",
                           y=-0.15,
                           yanchor="top")
    ],
    width=1400,
    height=700,
    margin=dict(
      l=0,  # left margin
      r=0,  # right margin
      b=0,  # bottom margin
      t=100,  # top margin
      pad=2  # padding
    ),
    font=dict(family="PT Sans Narrow", size=14, color="black"))

  fig.update_yaxes(
    tickformatstops=[
      dict(dtickrange=[0, 1],
           value=".2f"),  # Decimal notation for moderate values
      dict(dtickrange=[1, None],
           value=".2s")  # SI notation (e.g., K, M, B) for large values
    ],
    autorange=True)

  fig.update_xaxes(autorange=True)

  # Add event annotations and lines to the figure
  if 'events' in chart_template:
    for event in chart_template['events']:
      event_dates = pd.to_datetime(event['dates'])
      orientation = event.get('orientation', 'v')
      for date in event_dates:
        if orientation == 'v':  # vertical line
          fig.add_shape(type="line",
                        xref="x",
                        yref="paper",
                        x0=date.strftime("%Y-%m-%d"),
                        y0=0,
                        x1=date.strftime("%Y-%m-%d"),
                        y1=1,
                        line=dict(color="black", width=1, dash="dash"))
        elif orientation == 'h':  # horizontal line
          y_value = event.get('y_value', None)
          if y_value:  # make sure y_value is provided and is not zero
            fig.add_shape(type="line",
                          xref="paper",
                          yref="y",
                          x0=0,
                          y0=y_value,
                          x1=1,
                          y1=y_value,
                          line=dict(color="black", width=1, dash="dash"))
            fig.add_annotation(
              x=date.strftime("%Y-%m-%d"),
              y=y_value if orientation == 'h' else 1,
              text=event['name'],
              showarrow=False,
              font=dict(color="black"),
              xanchor="left",
              yanchor=
              "bottom"  # The bottom of the text aligns with the 'y' position
            )

  # Add watermark annotation to the figure
  fig.add_annotation(
    xref="paper",
    yref="paper",
    x=0.5,
    y=0.5,
    text="SecretSatoshis.com",
    showarrow=False,
    font=dict(size=50, color="rgba(128, 128, 128, 0.5)"),
    align="center",
  )
  # Add logo image as an annotation
  fig.add_layout_image(
    dict(
      source=
      "https://secretsatoshis.github.io/Bitcoin-Chart-Library/Secret_Satoshis_Logo.png",  # Ensure this path is correct
      x=0.0,
      y=1.2,
      sizex=0.1,
      sizey=0.1,  # Adjust size of the logo as needed
      xanchor="left",
      yanchor="top"))
  # Add data source annotation to the figure
  fig.add_annotation(
      text=chart_template['data_source'],  # Correct way to add the data source text
      xref="paper",
      yref="paper",
      x=1,
      y=-0.2,  # Position at the bottom right
      xanchor="right",
      yanchor="bottom",
      showarrow=False,
      font=dict(family="Arial", size=12, color="#666"),
      align="right",
  )

  # Save the chart as an HTML file
  filepath = 'Charts/' + filename + '.html'
  pio.write_html(fig, file=filepath, auto_open=False)

# Supply Chart
chart_supply = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcion Supply',
      'data': 'SplyCur',
      'yaxis': 'y'
    },
    {
      'name': 'Future Supply',
      'data': 'SplyExpFut10yr',
      'yaxis': 'y'
    },
    {
      'name': 'New Coins Issued 30 Day MA',
      'data': '30_day_ma_IssContNtv',
      'yaxis': 'y2'
    },
    {
      'name': 'New Coins Issued 365 Day MA',
      'data': '365_day_ma_IssContNtv',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Supply & Daily Issuance",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Supply",
  'y2_label':
  "New Bitcoins Created Each Day",
  'filename':
  "Bitcoin_Supply",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }]
}

# Transaction Chart
chart_transactions = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Transaction Count',
      'data': 'TxCnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Tx Count 30 Day MA',
      'data': '30_day_ma_TxCnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Tx Count 365 Day MA',
      'data': '365_day_ma_TxCnt',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Transactions",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Daily Transactions",
  'filename':
  "Bitcoin_Transactions",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Hashrate Chart
chart_hashrate = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Hash Rate',
      'data': 'HashRate',
      'yaxis': 'y2'
    },
    {
      'name': 'Hash Rate 30 Day MA',
      'data': '30_day_ma_HashRate',
      'yaxis': 'y2'
    },
    {
      'name': 'Hash Rate 365 Day MA',
      'data': '365_day_ma_HashRate',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Hashrate",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Network Hashrate",
  'filename':
  "Bitcoin_Hashrate",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Bitcoin Price Chart
chart_price = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price USD',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Bitcoin Marketcap USD',
    'data': 'CapMrktCurUSD',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Price",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "Bitcoin Market Cap (USD)",
  'filename':
  "Bitcoin_Price",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Transferred Value Chart
chart_transferred_value = {
  'x_data':
  'time',
  'y1_type':
  'linear',
  'y2_type':
  'log',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },
    {
      'name': 'Transaction Volume',
      'data': 'TxTfrValAdjUSD',
      'yaxis': 'y2'
    },
    {
      'name': 'Transaction Volume 30 Day MA',
      'data': '30_day_ma_TxTfrValAdjUSD',
      'yaxis': 'y2'
    },
    {
      'name': 'Transaction Volume 365 Day MA',
      'data': '365_day_ma_TxTfrValAdjUSD',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Transaction Volume",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Transaction Volume",
  'filename':
  "Bitcoin_Transaction_Value",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Miner Revenue Chart
chart_miner_revenue = {
  'x_data':
  'time',
  'y1_type':
  'linear',
  'y2_type':
  'log',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },
    {
      'name': 'Miner Revenue',
      'data': 'RevUSD',
      'yaxis': 'y2'
    },
    {
      'name': 'Miner Revenue 30 Day MA',
      'data': '30_day_ma_RevUSD',
      'yaxis': 'y2'
    },
    {
      'name': 'Miner Revenue 365 Day MA',
      'data': '365_day_ma_RevUSD',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Miner Revenue",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Miner Revenue",
  'filename':
  "Bitcoin_Miner_Revenue",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Active Addresses Chart
chart_active_addresses = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },
    {
      'name': 'Active Addresses',
      'data': 'AdrActCnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Addresses 30 Day MA',
      'data': '30_day_ma_AdrActCnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Addresses 365 Day MA',
      'data': '365_day_ma_AdrActCnt',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Active Addresses",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Active Addresses",
  'filename':
  "Bitcoin_Active_Addresses",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Transaction Size Chart
chart_transaction_size = {
  'x_data':
  'time',
  'y1_type':
  'linear',
  'y2_type':
  'log',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': '30 Day Avg Tx Value',
    'data': '30_day_ma_TxTfrValMeanUSD',
    'yaxis': 'y2'
  }, {
    'name': '30 Day Median Tx Value',
    'data': '30_day_ma_TxTfrValMedUSD',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Transaction Size ",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Transaction Size",
  'filename':
  "Bitcoin_Transaction_Size",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Transaction Fee USD Chart
chart_transaction_fee_USD = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },
    {
      'name': 'Fees Paid (USD)',
      'data': 'FeeTotUSD',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Fees In USD",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Fees In US Dollars",
  'filename':
  "Bitcoin_Transaction_Fee",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Address Balance Count USD Chart
chart_address_balance = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },
    {
      'name': 'Total Bitcoin Addresses',
      'data': 'AdrBalCnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Address Balance USD 1',
      'data': 'AdrBalUSD1Cnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Address Balance USD 10',
      'data': 'AdrBalUSD10Cnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Address Balance USD 1k',
      'data': 'AdrBalUSD1KCnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Address Balance USD 10k',
      'data': 'AdrBalUSD10KCnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Address Balance USD 1M',
      'data': 'AdrBalUSD1MCnt',
      'yaxis': 'y2'
    },
    {
      'name': 'Address Balance USD 10M',
      'data': 'AdrBalUSD10MCnt',
      'yaxis': 'y2'
    }
  ],
  'title':
  "Address Balances",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Address Balance Count",
  'filename':
  "Bitcoin_Address_Balance",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# 1+ Year Active Supply Chart
chart_1_year_supply = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },
    {
      'name': '1+ Year Active Supply',
      'data': 'supply_pct_1_year_plus',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin 1+ Year Supply",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "1+ Year Supply Percentage",
  'filename':
  "Bitcoin_1_Year_Supply",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Macro Supply
macro_supply = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Liquid Supply',
    'data': 'liquid_supply',
    'yaxis': 'y2'
  }, {
    'name': 'Illiquid Supply',
    'data': 'illiquid_supply',
    'yaxis': 'y2'
  }, {
    'name': 'Miner Supply',
    'data': 'SplyMiner0HopAllNtv',
    'yaxis': 'y2'
  }, {
    'name': '1 Hop Miner Supply',
    'data': 'SplyMiner1HopAllNtv',
    'yaxis': 'y2'
  }, {
    'name': 'Daily Tx Amount',
    'data': 'TxTfrValAdjNtv',
    'yaxis': 'y2'
  }, {
    'name': 'Current Supply',
    'data': 'SplyCur',
    'yaxis': 'y2'
  }, {
    'name': 'Future Supply',
    'data': 'SplyExpFut10yr',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Macro Supply",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Bitcoins Supply",
  'filename':
  "Bitcoin_Macro_Supply",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Thermocap Price Multiple Chart
chart_thermocap_multiple = {
  'x_data':
  'time',
  'y2_type':
  'linear',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
     'name': 'Thermocap Price',
     'data': 'thermocap_price',
     'yaxis': 'y'
  },{
    'name': '4x Thermocap Price Multiple',
    'data': 'thermocap_price_multiple_4',
    'yaxis': 'y'
  }, {
    'name': '8x Thermocap Price Multiple',
    'data': 'thermocap_price_multiple_8',
    'yaxis': 'y'
  }, {
    'name': '16x Thermocap Price Multiple',
    'data': 'thermocap_price_multiple_16',
    'yaxis': 'y'
  }, {
    'name': '32x Thermocap Price Multiple',
    'data': 'thermocap_price_multiple_32',
    'yaxis': 'y'
  }, {
    'name': 'Thermocap Multiple',
    'data': 'thermocap_multiple',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Thermocap Multiple",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Thermocap Multiple",
  'filename':
  "Bitcoin_Thermocap_Multiples",
  'chart_type':
  'line',
  'filter_start_date': '2012-01-01',   
  'filter_metric': 'thermocap_multiple',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Realized Price Multiple Chart
chart_realizedcap_multiple = {
  'x_data':
  'time',
  'y1_type':
  'log',
  'y2_type':
  'linear',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Realized Price',
    'data': 'realised_price',
    'yaxis': 'y'
  }, {
    'name': '3x Realized Price',
    'data': 'realizedcap_multiple_3',
    'yaxis': 'y'
  }, {
    'name': '5x Realized Price',
    'data': 'realizedcap_multiple_5',
    'yaxis': 'y'
  }, {
    'name': 'Realized Price Multiple ',
    'data': 'CapMVRVCur',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Realized Price",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "MVRV Ratio",
  'filename':
  "Bitcoin_Realized_Price",
  'chart_type':
  'line',
  'filter_start_date': '2012-01-01',   
  'filter_metric': 'CapMVRVCur',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# NVT Price  Chart
chart_nvt_price = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  },{
    'name': 'NVT Price 30 Day MA',
    'data': '30_day_ma_nvt_price',
    'yaxis': 'y'
  },{
    'name': 'NVT Price 365 Day MA',
    'data': '365_day_ma_nvt_price',
    'yaxis': 'y'
  },{
    'name': 'NVT Ratio 2 Year Median',
    'data': 'nvt_price_multiple_ma',
    'yaxis': 'y2'
            }],
  'title':
  "Bitcoin NVT Price",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "NVT Ratio",
  'filename':
  "Bitcoin_NVT_Price",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Electricity Price Chart
electricity_price = {
  'x_data':
  'time',
  'y2_type':
  'log',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Energy Value',
    'data': 'Lagged_Energy_Value',
    'yaxis': 'y'
  }, {
     'name': 'Bitcoin Production Cost',
     'data': 'Bitcoin_Production_Cost',
      'yaxis': 'y'
  }, {
     'name': 'Electricity Cost',
     'data': 'Electricity_Cost',
     'yaxis': 'y'
  }, {
      'name': 'Energy Value Multiple',
      'data': 'Energy_Value_Multiple',
      'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Production Price",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':"",
  'filename':
  "Bitcoin_Production_Price",
  'chart_type':
  'line',
  #'filter_start_date': '2014-01-01',   
  #'filter_metric': 'Energy_Value_Multiple',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Stock To Flow Chart
s2f_price = {
  'x_data':
  'time',
  'y2_type':
  'log',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Stock-To-Flow Price',
    'data': 'SF_Predicted_Price',
    'yaxis': 'y'
  }, {
    'name': 'Stock-To-Flow Multiple',
    'data': 'SF_Multiple',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Stock To Flow Price",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':"Stock To Flow Multiple",
  'filename':
  "Bitcoin_S2F_Price",
  'chart_type':
  'line',
  #'filter_start_date': '2012-01-01',   
  #'filter_metric': 'thermocap_multiple',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# NUPL Chart
chart_NUPL = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },
    {
      'name': 'Net Unrealized Profit Loss',
      'data': 'nupl',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Net Unrealized Profit Loss Ratio",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "NUPL Ratio",
  'filename':
  "Bitcoin_NUPL",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Bitcoin Price Chart
chart_price_ma = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': '50 Day MA',
    'data': '50_day_ma_priceUSD',
    'yaxis': 'y'
  }, {
    'name': '200 Day MA',
    'data': '200_day_ma_priceUSD',
    'yaxis': 'y'
  }, {
    'name': '200 Week MA',
    'data': '200_week_ma_priceUSD',
    'yaxis': 'y'
  }, {
    'name': '200 Day MA Multiple',
    'data': '200_day_multiple',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Price Moving Averages",
  'filter_start_date': '2012-01-01',   
  'filter_metric': 'PriceUSD',
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "200 Day Moving Average Multiple",
  'filename':
  "Bitcoin_Price_Chart_MA",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankruptcy',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures Launch',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankruptcy',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# ATH Drawdown Chart
chart_drawdowns = {
  'x_data':
  'days_since_ath',
  'y_data': [
    {
      'name': 'Drawdown Cycle 1',
      'data': 'drawdown_cycle_1',
      'yaxis': 'y'
    },
    {
      'name': 'Drawdown Cycle 2',
      'data': 'drawdown_cycle_2',
      'yaxis': 'y'
    },
    {
      'name': 'Drawdown Cycle 3',
      'data': 'drawdown_cycle_3',
      'yaxis': 'y'
    },
    {
      'name': 'Drawdown Cycle 4',
      'data': 'drawdown_cycle_4',
      'yaxis': 'y'
    },
  ],
  'title':
  "Bitcoin Drawdowns",
  'x_label':
  "Days since ATH",
  'y1_label':
  "Drawdown (%)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_ATH_Drawdown",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
}

# Cycle Low Chart
chart_cycle_lows = {
  'x_data':
  'days_since_cycle_low',
  'y1_type':
  'log',
  'y_data': [
    {
      'name': 'Market Cycle 1',
      'data': 'return_since_cycle_low_1',
      'yaxis': 'y'
    },
    {
      'name': 'Market Cycle 2',
      'data': 'return_since_cycle_low_2',
      'yaxis': 'y'
    },
    {
      'name': 'Market Cycle 3',
      'data': 'return_since_cycle_low_3',
      'yaxis': 'y'
    },
    {
      'name': 'Market Cycle 4',
      'data': 'return_since_cycle_low_4',
      'yaxis': 'y'
    },
    {
      'name': 'Market Cycle 5',
      'data': 'return_since_cycle_low_5',
      'yaxis': 'y'
    },
  ],
  'title':
  "Bitcoin Return From Cycle Low",
  'x_label':
  "Days Since Cycle Low",
  'y1_label':
  "Return (%)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_Cycle_Low",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
}

# Halving Performane Chart
chart_halvings = {
  'x_data':
  'days_since_halving',
  'y_data': [
    {
      'name': 'Halving Era 2',
      'data': 'return_since_halving_2',
      'yaxis': 'y'
    },
    {
      'name': 'Halving Era 3',
      'data': 'return_since_halving_3',
      'yaxis': 'y'
    },
    {
      'name': 'Halving Era 4',
      'data': 'return_since_halving_4',
      'yaxis': 'y'
    },
  ],
  'title':
  "Bitcoin Halvings Return Comparison",
  'x_label':
  "Days Since Halving",
  'y1_label':
  "Return (%)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_Halving_Cycle",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
}

# Bitcoin YOY Retrun Comparison
yoy_return = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin YOY Return',
    'data': 'PriceUSD_YOY_change',
    'yaxis': 'y2'
  }, {
     'name': 'Bitcoin Price',
     'data': 'PriceUSD',
      'yaxis': 'y'
            }],
  'title':
  "Year Over Year Return",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "Year Over Year Return (Percentage)",
  'filter_start_date': '2015-01-01',   
  'filter_metric': 'PriceUSD_YOY_change',
  'filename':
  "Bitcoin_YOY_Return",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
}

# Bitcoin CAGR Comparison
cagr_overview = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },{
      'name': 'Bitcoin 4 Year CAGR',
      'data': 'PriceUSD_4_Year_CAGR',
      'yaxis': 'y2'
    }],
  'title':
  "4 Year Compound Annual Growth Rate",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "4 Year CAGR (Percentage)",
  'filter_start_date': '2015-01-01',   
  'filter_metric': 'PriceUSD_4_Year_CAGR',
  'filename':
  "Bitcoin_CAGR",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
}

# Bitcoin m0
chart_m0 = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'United States',
    'data': 'United_States_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'China',
    'data': 'China_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Eurozone',
    'data': 'Eurozone_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Japan',
    'data': 'Japan_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'United Kingdom',
    'data': 'United_Kingdom_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Switzerland',
    'data': 'Switzerland_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'India',
    'data': 'India_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Australia',
    'data': 'Australia_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Russia',
    'data': 'Russia_btc_price',
    'yaxis': 'y'
  }],
  'title':
  "Bitcoin Price VS M0 Money Supply",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_M0",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankruptcy',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures Launch',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankruptcy',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Equities Market Cap Chart
chart_equities = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'AAPL',
    'data': 'AAPL_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'MSFT',
    'data': 'MSFT_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'GOOGL',
    'data': 'GOOGL_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'AMZN',
    'data': 'AMZN_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'NVDA',
    'data': 'NVDA_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'TSLA',
    'data': 'TSLA_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'V',
    'data': 'V_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'JPM',
    'data': 'JPM_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'PYPL',
    'data': 'PYPL_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'GS',
    'data': 'GS_mc_btc_price',
    'yaxis': 'y'
  }],
  'title':
  "Bitcoin Price VS Equities Market Cap",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_Equities",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Gold Market Cap Chart
chart_gold = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Gold Marketcap',
    'data': 'gold_marketcap_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Silver Marketcap',
    'data': 'silver_marketcap_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Gold Jewellery',
    'data': 'gold_jewellery_marketcap_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Gold Private Investment',
    'data': 'gold_private_investment_marketcap_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Gold Country Holdings',
    'data': 'gold_official_country_holdings_marketcap_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Gold Other / Industrial',
    'data': 'gold_other_marketcap_btc_price',
    'yaxis': 'y'
  }],
  'title':
  "Bitcoin Price VS Gold Market Cap",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_Gold",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Bitcoin Promo Chart
chart_promo = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Realized Price',
    'data': 'realised_price',
    'yaxis': 'y'
  }, {
    'name': 'Thermocap Multiple 32x',
    'data': 'thermocap_price_multiple_32',
    'yaxis': 'y'
  }, {
    'name': '200 Week MA',
    'data': '200_week_ma_priceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Hash Rate 30 Day MA',
    'data': '30_day_ma_HashRate',
    'yaxis': 'y2'
  }, {
    'name': 'Hash Rate 365 Day MA',
    'data': '365_day_ma_HashRate',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin 101",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "HashRate",
  'filename':
  "Bitcoin_Promo",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankruptcy',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures Launch',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankruptcy',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Bitcoin Relative Valuation
chart_rv = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Silver',
    'data': 'silver_marketcap_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Gold',
    'data': 'gold_marketcap_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'Apple',
    'data': 'AAPL_mc_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'United States',
    'data': 'United_States_btc_price',
    'yaxis': 'y'
  }, {
    'name': 'United Kingdom',
    'data': 'United_Kingdom_btc_price',
    'yaxis': 'y'
  }],
  'title':
  "Bitcoin Price Relative Valuation",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_RV",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankruptcy',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures Launch',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankruptcy',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Bitcoin On-Chain
chart_on_chain = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'NVT Price 30 Day MA',
    'data': '30_day_ma_nvt_price',
    'yaxis': 'y'
  }, {
    'name': '8x Thermocap Multiple',
    'data': 'thermocap_price_multiple_8',
    'yaxis': 'y'
  }, {
    'name': '16x Thermocap Multiple',
    'data': 'thermocap_price_multiple_16',
    'yaxis': 'y'
  }, {
    'name': 'Realized Price',
    'data': 'realised_price',
    'yaxis': 'y'
  }, {
    'name': '3x Realized Price',
    'data': 'realizedcap_multiple_3',
    'yaxis': 'y'
  }],
  'title':
  "Bitcoin Price On-Chain Value",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_On_Chain",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankruptcy',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures Launch',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankruptcy',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Bitcoin YTD Retrun Comparison
mtd_return = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin',
    'data': 'PriceUSD_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'Nasdaq',
    'data': '^IXIC_close_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'S&P500',
    'data': '^GSPC_close_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'XLF Financials ETF',
    'data': 'XLF_close_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'XLE Energy ETF',
    'data': 'XLE_close_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'FANG+ ETF',
    'data': 'FANG.AX_close_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'BITQ Crypto Industry ETF',
    'data': 'BITQ_close_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'Gold Futures',
    'data': 'GC=F_close_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'US Dollar Futures',
    'data': 'DX=F_close_MTD_change',
    'yaxis': 'y'
  }, {
    'name': 'TLT Treasury Bond ETF',
    'data': 'TLT_close_MTD_change',
    'yaxis': 'y'
  }],
  'title':
  "Month To Date Return Comparison",
  'x_label':
  "Date",
  'y1_label':
  "Month To Date Return (Percentage)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_MTD_Return_Comparison",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
}

# Hashrate Chart
chart_sats_per_dollar = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Satoshis Per Dollar',
    'data': 'sat_per_dollar',
    'yaxis': 'y1'
  }, {
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y2'
  }],
  'title':
  "Satoshis Per Dollar",
  'x_label':
  "Date",
  'y1_label':
  "Satoshis Per Dollar | Amount Of Bitcoin You Can Purchase Per $1",
  'y2_label':
  "1 Full Bitcion Price",
  'filename':
  "Bitcoin_Sats_Per_Dollar",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Bitcoin Promo Chart
chart_hashrate_price = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Hash Rate',
    'data': 'HashRate',
    'yaxis': 'y2'
  }, {
    'name': 'Hash Rate 30 Day MA',
    'data': '30_day_ma_HashRate',
    'yaxis': 'y2'
  }, {
    'name': 'Hash Rate 365 Day MA',
    'data': '365_day_ma_HashRate',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Price & Hashrate",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "HashRate",
  'filename':
  "Bitcoin_Hashrate_Price",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankruptcy',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures Launch',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankruptcy',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Transaction Chart
chart_transactions_volume = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Tx Count',
    'data': 'TxCnt',
    'yaxis': 'y'
  }, {
    'name': 'Tx Count 30 Day MA',
    'data': '30_day_ma_TxCnt',
    'yaxis': 'y'
  }, {
    'name': 'Tx Count 365 Day MA',
    'data': '365_day_ma_TxCnt',
    'yaxis': 'y'
  }, {
    'name': 'Transaction Volume',
    'data': 'TxTfrValAdjUSD',
    'yaxis': 'y2'
  }, {
    'name': 'Transaction Volume 30 Day MA',
    'data': '30_day_ma_TxTfrValAdjUSD',
    'yaxis': 'y2'
  }, {
    'name': 'Transaction Volume 365 Day MA',
    'data': '365_day_ma_TxTfrValAdjUSD',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Transaction Count & Transaction Volume",
  'x_label':
  "Date",
  'y1_label':
  "Transaction Count",
  'y2_label':
  "Transaction Volume",
  'filename':
  "Bitcoin_Transactions_Volume",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Address Balance Count USD Chart
chart_address_balance_comp = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcon Price',
    'data': 'PriceUSD',
    'yaxis': 'y'
  }, {
    'name': 'Address Balance USD 10',
    'data': 'AdrBalUSD10Cnt',
    'yaxis': 'y2'
  }, {
    'name': 'Active Addresses',
    'data': 'AdrActCnt',
    'yaxis': 'y2'
  }, {
    'name': 'Active Addresses 30 Day MA',
    'data': '30_day_ma_AdrActCnt',
    'yaxis': 'y2'
  }, {
    'name': 'Active Addresses 365 Day MA',
    'data': '365_day_ma_AdrActCnt',
    'yaxis': 'y2'
  }],
  'title':
  "Bitcoin Address Breakdown",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price (USD)",
  'y2_label':
  "Address Count",
  'filename':
  "Bitcoin_Address_Balance_Comp",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Address Balance Count USD Chart
chart_address_balance_supply_comp = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Address Balance With +10 USD',
      'data': 'AdrBalUSD10Cnt',
      'yaxis': 'y'
    },
    {
      'name': '1+ Year Active Supply',
      'data': 'supply_pct_1_year_plus',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Bitcoin Supply Age & Address Balance Count",
  'x_label':
  "Date",
  'y1_label':
  "Addresses With +10 USD Balance",
  'y2_label':
  "+1 Year Old Supply (Percentage)",
  'filename':
  "Bitcoin_Address_Supply_Comp",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Supply Balance Count USD Chart
chart_supply_age = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcoin Price',
      'data': 'PriceUSD',
      'yaxis': 'y'
    },
    {
      'name': 'Active Supply 1 Day',
      'data': 'SplyAct1d',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 30 Days',
      'data': 'SplyAct30d',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 90 Days',
      'data': 'SplyAct90d',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 180 Days',
      'data': 'SplyAct180d',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 1 Year',
      'data': 'SplyAct1yr',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 2 Years',
      'data': 'SplyAct2yr',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 3 Years',
      'data': 'SplyAct3yr',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 4 Years',
      'data': 'SplyAct4yr',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 5 Years',
      'data': 'SplyAct5yr',
      'yaxis': 'y2'
    },
    {
      'name': 'Active Supply 10 Years',
      'data': 'SplyAct10yr',
      'yaxis': 'y2'
    },
    {
      'name': 'Current Supply',
      'data': 'SplyCur',
      'yaxis': 'y2'
    },
  ],
  'title':
  "Supply Age",
  'x_label':
  "Date",
  'y1_label':
  "Bitcoin Price",
  'y2_label':
  "Supply Of Bitcoin",
  'filename':
  "Bitcoin_Supply_Age",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
  'events': [{
    'name': 'Halving',
    'dates': ['2012-11-28', '2016-07-09', '2020-05-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Launch',
    'dates': ['2010-07-01'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Hack',
    'dates': ['2011-06-11'],
    'orientation': 'v'
  }, {
    'name': 'MtGox Bankrupt',
    'dates': ['2014-02-01'],
    'orientation': 'v'
  }, {
    'name': 'BitLicense',
    'dates': ['2015-08-08'],
    'orientation': 'v'
  }, {
    'name': 'CME Futures',
    'dates': ['2017-12-17'],
    'orientation': 'v'
  }, {
    'name': 'Bitcoin Winter',
    'dates': ['2018-12-15'],
    'orientation': 'v'
  }, {
    'name': 'Coinbase IPO',
    'dates': ['2021-04-14'],
    'orientation': 'v'
  }, {
    'name': 'FTX Bankrupt',
    'dates': ['2022-11-11'],
    'orientation': 'v'
  }]
}

# Bitcoin CAGR Comparison
cagr_comparison = {
  'x_data':
  'time',
  'y_data': [
    {
      'name': 'Bitcoin',
      'data': 'PriceUSD_4_Year_CAGR',
      'yaxis': 'y'
    },
    {
      'name': 'Nasdaq',
      'data': '^IXIC_close_4_Year_CAGR',
      'yaxis': 'y'
    },
    {
      'name': 'S&P500',
      'data': '^GSPC_close_4_Year_CAGR',
      'yaxis': 'y'
    },
    {
      'name': 'XLF Financials ETF',
      'data': 'XLF_close_4_Year_CAGR',
      'yaxis': 'y'
    },
    {
      'name': 'XLE Energy ETF',
      'data': 'XLE_close_4_Year_CAGR',
      'yaxis': 'y'
    },
    {
      'name': 'FANG+ ETF',
      'data':
      'FANG.AX_close_2_Year_CAGR',  # Using 2-Year CAGR as provided in the template
      'yaxis': 'y'
    },
    {
      'name': 'BITQ Crypto Industry ETF',
      'data':
      'BITQ_close_2_Year_CAGR',  # Using 2-Year CAGR as provided in the template
      'yaxis': 'y'
    },
    {
      'name': 'Gold Futures',
      'data': 'GC=F_close_4_Year_CAGR',
      'yaxis': 'y'
    },
    {
      'name': 'US Dollar Futures',
      'data': 'DX=F_close_4_Year_CAGR',
      'yaxis': 'y'
    },
    {
      'name': 'TLT Treasury Bond ETF',
      'data': 'TLT_close_4_Year_CAGR',
      'yaxis': 'y'
    }
  ],
  'title':
  "4 Year Compound Annual Growth Rate Comparison",
  'x_label':
  "Date",
  'y1_label':
  "4 Year CAGR (Percentage)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_CAGR_Comparison",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
}

# Bitcoin YTD Retrun Comparison
ytd_return = {
  'x_data':
  'time',
  'y_data': [{
    'name': 'Bitcoin',
    'data': 'PriceUSD_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'Nasdaq',
    'data': '^IXIC_close_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'S&P500',
    'data': '^GSPC_close_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'XLF Financials ETF',
    'data': 'XLF_close_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'XLE Energy ETF',
    'data': 'XLE_close_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'FANG+ ETF',
    'data': 'FANG.AX_close_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'BITQ Crypto Industry ETF',
    'data': 'BITQ_close_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'Gold Futures',
    'data': 'GC=F_close_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'US Dollar Futures',
    'data': 'DX=F_close_YTD_change',
    'yaxis': 'y'
  }, {
    'name': 'TLT Treasury Bond ETF',
    'data': 'TLT_close_YTD_change',
    'yaxis': 'y'
  }],
  'title':
  "Year To Date Return",
  'x_label':
  "Date",
  'y1_label':
  "Year To Date Return (Percentage)",
  'y2_label':
  "",
  'filename':
  "Bitcoin_YTD_Return_Comparison",
  'chart_type':
  'line',
  'data_source':
  "Data Source: CoinMetrics",
}

# List Of All Chart Templates
chart_templates = [
  chart_supply, chart_transactions, chart_hashrate, chart_price,
  chart_transferred_value, chart_miner_revenue, chart_active_addresses,
  chart_transaction_size, chart_transaction_fee_USD, chart_address_balance,
  macro_supply, chart_1_year_supply, chart_supply_age, 
  chart_thermocap_multiple, chart_realizedcap_multiple, chart_nvt_price, 
  chart_NUPL, electricity_price, s2f_price,
  chart_price_ma, yoy_return, cagr_overview,
  chart_m0, chart_equities, chart_gold, chart_promo,
  chart_rv, chart_on_chain, chart_sats_per_dollar,
  chart_hashrate_price, chart_transactions_volume, chart_address_balance_comp,
  chart_address_balance_supply_comp, mtd_return, cagr_comparison, ytd_return
]

# Map the chart types to their respective functions
chart_creators = {'line': create_line_chart}

# Create Charts Function
def create_charts(selected_metrics, chart_templates):
  figures = []
  for chart_template in chart_templates:
    chart_type = chart_template.get(
      'chart_type', 'line')  # Default to 'line' if no chart_type specified
    chart_creator = chart_creators[
      chart_type]  # This will be the function that creates the chart
    fig = chart_creator(chart_template, selected_metrics)
    figures.append(fig)
  return figures
