import requests
import pandas as pd
from io import StringIO
from yahoo_fin import stock_info as si
import numpy as np
from scipy.stats import linregress
from pandas.tseries.offsets import MonthEnd
from datetime import datetime
from datetime import timedelta
import time

def get_coinmetrics_onchain(endpoint):
    url = f'https://raw.githubusercontent.com/coinmetrics/data/master/csv/{endpoint}'
    response = requests.get(url)
    data = pd.read_csv(StringIO(response.text), low_memory=False)
    data['time'] = pd.to_datetime(data['time'])
    print("Coinmetrics Data Call Completed")
    return data

def get_fear_and_greed_index():
    url = "https://api.alternative.me/fng/?limit=0"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data['data'])
    df['time'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')  # convert unix timestamp to datetime
    df = df[['value', 'value_classification',
             'time']]  # select only the required columns
    print("Fear & Greed Data Call Completed")
    return df

def get_price(tickers, start_date):
      data = pd.DataFrame()
      for category, ticker_list in tickers.items():
          for ticker in ticker_list:
              try:
                  stock = si.get_data(ticker, start_date=start_date)
                  stock = stock[['close']]  # Keep only the 'close' column
                  stock.columns = [ticker + '_close']  # Rename the column
                  stock = stock.resample('D').ffill()  # Resample to fill missing days
                  if data.empty:
                      data = stock
                  else:
                      data = data.join(stock)
              except Exception as e:
                  print(f"Could not fetch data for {ticker} in category {category}. Reason: {str(e)}")
      data.reset_index(inplace=True)
      data.rename(columns={'index': 'time'}, inplace=True)  # rename 'date' to 'time'
      data['time'] = pd.to_datetime(data['time'])  # convert to datetime type
      print("Yahoo Finance Price Data Call Completed")
      return data

def get_marketcap(tickers, start_date):
    date_range = pd.date_range(start=start_date, end=pd.to_datetime('today'))
    data = pd.DataFrame(date_range, columns=['time'])

    # Only get market cap for the tickers in the 'stocks' category
    stock_tickers = tickers['stocks']

    for ticker in stock_tickers:
      quote_table = None  # Initialize quote_table to None
      try:
        quote_table = si.get_quote_table(ticker)
        market_cap_str = quote_table["Market Cap"]

        # Convert market cap to numeric
        if 'T' in market_cap_str:
          market_cap = float(market_cap_str.replace('T', '')) * 1e12
        elif 'B' in market_cap_str:
          market_cap = float(market_cap_str.replace('B', '')) * 1e9
        elif 'M' in market_cap_str:
          market_cap = float(market_cap_str.replace('M', '')) * 1e6
        elif 'K' in market_cap_str:
          market_cap = float(market_cap_str.replace('K', '')) * 1e3
        else:
          market_cap = float(market_cap_str)

        # Create a new column for this ticker's market cap and backfill it with the current market cap
        data[f'{ticker}_MarketCap'] = [market_cap
                                       ] + [None] * (len(date_range) - 1)
        data[f'{ticker}_MarketCap'] = data[f'{ticker}_MarketCap'].ffill()
      except Exception as e:
        print(f"Could not fetch data for {ticker}. Reason: {str(e)}")
        print(f"Quote table for {ticker}: {quote_table}")
        data[f'{ticker}_MarketCap'] = [None] * len(date_range)
    print("Yahoo Finance Marketcap Data Call Completed")
    return data

def calculate_custom_on_chain_metrics(data):
  # New Metrics Based On Coinmetrics Data
      data['sat_per_dollar'] = 1 / (data['PriceUSD'] /100000000)
      data['mvrv_ratio'] = data['CapMrktCurUSD'] / data['CapRealUSD']
      data['realised_price'] = data['CapRealUSD'] / data['SplyCur']
      data['nupl'] = (data['CapMrktCurUSD'] - data['CapRealUSD']) / data['CapMrktCurUSD']
      data['nvt_price'] = (data['NVTAdj'].rolling(window=365*2).median() * data['TxTfrValAdjUSD']) / data['SplyCur']
      data['nvt_price_adj'] = (data['NVTAdj90'].rolling(window=365).median() * data['TxTfrValAdjUSD']) / data['SplyCur']
      data['nvt_price_multiple'] = data['PriceUSD'] / data['nvt_price']

  # Price Moving Averages
      data['7_day_ma_priceUSD'] = data['PriceUSD'].rolling(window=7).mean()
      data['50_day_ma_priceUSD'] = data['PriceUSD'].rolling(window=50).mean()
      data['100_day_ma_priceUSD'] = data['PriceUSD'].rolling(window=100).mean()
      data['200_day_ma_priceUSD'] = data['PriceUSD'].rolling(window=200).mean()
      data['200_week_ma_priceUSD'] = data['PriceUSD'].rolling(window=200 * 7).mean()

  # Price Multiple
      data['200_day_multiple'] = data['PriceUSD'] / data['200_day_ma_priceUSD']

      # Thermocap Multiple
      data['thermocap_multiple'] = data['CapMrktCurUSD'] / data['RevAllTimeUSD']
      data['thermocap_multiple_4'] = (4 * data['RevAllTimeUSD']) / data['SplyCur']
      data['thermocap_multiple_8'] = (8 * data['RevAllTimeUSD']) / data['SplyCur']
      data['thermocap_multiple_16'] = (16 * data['RevAllTimeUSD']) / data['SplyCur']
      data['thermocap_multiple_32'] = (32 *data['RevAllTimeUSD']) / data['SplyCur']

      # Realized Cap Multiple
      data['realizedcap_multiple_3'] = (3 * data['CapRealUSD']) / data['SplyCur']
      data['realizedcap_multiple_5'] = (5 * data['CapRealUSD']) / data['SplyCur']
      data['realizedcap_multiple_7'] = (7 * data['CapRealUSD']) / data['SplyCur']

      # 1+ Year Supply %
      data['supply_pct_1_year_plus'] = (100 - data['SplyActPct1yr'])
      data['illiquid_supply'] = ((data['supply_pct_1_year_plus'] / 100) *data['SplyCur'])
      data['liquid_supply'] = (data['SplyCur'] - data['illiquid_supply'])
      print("Custom Metrics Created")
      return data

def calculate_moving_averages(data, metrics):
      # Calculate moving averages for each metric
      for metric in metrics:
          data[f'7_day_ma_{metric}'] = data[metric].rolling(window=7).mean()
          data[f'30_day_ma_{metric}'] = data[metric].rolling(window=30).mean()
          data[f'365_day_ma_{metric}'] = data[metric].rolling(window=365).mean()

      return data

def calculate_metal_market_caps(data, gold_silver_supply):
      for i, row in gold_silver_supply.iterrows():
          metal = row['Metal']
          supply_billion_troy_ounces = row['Supply in Billion Troy Ounces']

          # Compute the market cap in billion USD
          if metal == 'Gold':
              price_usd_per_ounce = data['GC=F_close']
          elif metal == 'Silver':
              price_usd_per_ounce = data['SI=F_close']

          metric_name = metal.lower() + '_marketcap_billion_usd'
          data[metric_name] = supply_billion_troy_ounces * price_usd_per_ounce
      return data

def calculate_gold_market_cap_breakdown(data, gold_supply_breakdown):
      gold_marketcap_billion_usd = data['gold_marketcap_billion_usd'].iloc[-1]  # get the latest value
      for i, row in gold_supply_breakdown.iterrows():
          category = row['Gold Supply Breakdown']
          percentage_of_market = row['Percentage Of Market']

          # Compute the market cap for this category
          category_marketcap_billion_usd = gold_marketcap_billion_usd * (percentage_of_market / 100.0)

          # Add a new metric to the data
          metric_name = 'gold_marketcap_' + category.replace(' ', '_').lower() + '_billion_usd'
          data[metric_name] = category_marketcap_billion_usd  
      return data
  
def calculate_btc_price_to_surpass_metal_categories(data, gold_supply_breakdown):
  # Calculate for the overall gold market cap
  gold_marketcap_billion_usd = data['gold_marketcap_billion_usd'].iloc[-1]  # get the latest value
  gold_marketcap_usd = gold_marketcap_billion_usd  # Convert to just units
  data['gold_marketcap_btc_price'] = gold_marketcap_usd / data['SplyCur'].iloc[-2]

  # Calculate for gold subcategories
  for i, row in gold_supply_breakdown.iterrows():
      category = row['Gold Supply Breakdown']
      percentage_of_market = row['Percentage Of Market']

      # Compute the market cap for this category
      category_marketcap_billion_usd = gold_marketcap_billion_usd * (percentage_of_market / 100.0)
      category_marketcap_usd = category_marketcap_billion_usd # Convert to just units

      # Create the desired metric name format
      if category == "Jewellery":
          metric_name = 'gold_jewellery_marketcap_btc_price'
      elif category == "Private Investment":
          metric_name = 'gold_private_investment_marketcap_btc_price'
      elif category == "Official Country Holdings":
          metric_name = 'gold_country_holdings_marketcap_btc_price'
      elif category == "Other":
          metric_name = 'gold_other_marketcap_btc_price'

      # Compute the price of Bitcoin needed to surpass this gold category's market cap
      data[metric_name] = category_marketcap_usd / data['SplyCur'].iloc[-2]

  # Now, calculate for silver
  silver_marketcap_billion_usd = data['silver_marketcap_billion_usd'].iloc[-1]
  silver_marketcap_usd = silver_marketcap_billion_usd  # Convert to just units
  data['silver_marketcap_btc_price'] = silver_marketcap_usd / data['SplyCur'].iloc[-2]

  return data

def calculate_btc_price_to_surpass_fiat(data, fiat_money_data):
      for i, row in fiat_money_data.iterrows():
          country = row['Country']
          fiat_supply_usd_trillion = row['US Dollar Trillion']

          # Convert the fiat supply from trillions to just units
          fiat_supply_usd = fiat_supply_usd_trillion * 1e12

          # Compute the price of Bitcoin needed to surpass this country's M0 money supply
          metric_name_price = country.replace(" ", "_") + '_btc_price'
          metric_name_cap = country.replace(" ", "_") + '_cap'
          data[metric_name_price] = fiat_supply_usd / data['SplyCur']
          data[metric_name_cap] = fiat_supply_usd 
      return data

def calculate_btc_price_for_stock_mkt_caps(data, stock_tickers):
      new_columns = {}
      for ticker in stock_tickers:
          new_columns[ticker + '_mc_btc_price'] = data[ticker + '_MarketCap'] / data['SplyCur']
      data = pd.concat([data, pd.DataFrame(new_columns)], axis=1)
      return data

def calculate_stock_to_flow_metrics(data):
    # Extract the start of each month's data
    btc_monthly_data = data.resample('M').first()

    # Calculate the monthly flow
    btc_monthly_data['Flow'] = btc_monthly_data['SplyCur'].diff() * 12

    # Calculate Stock-to-Flow
    btc_monthly_data['SF'] = btc_monthly_data['SplyCur'] / btc_monthly_data['Flow']

    # Extract the monthly average price and add it to the resampled data
    btc_monthly_data['PriceUSD'] = data['PriceUSD'].resample('M').mean()

    # Removing the first row as it doesn't have a valid SF value due to the diff operation
    btc_monthly_data = btc_monthly_data[1:]

    # Extracting the relevant columns
    sf_data = btc_monthly_data[['SplyCur', 'Flow', 'SF', 'PriceUSD']].dropna()

    # Applying the provided linear regression formula
    btc_monthly_data['SF_Predicted_Market_Value'] = np.exp(14.6) * btc_monthly_data['SF']**3.3

    # Calculating the predicted market price by dividing the Predicted Market Value by the supply for that month
    btc_monthly_data['SF_Predicted_Price'] = btc_monthly_data['SF_Predicted_Market_Value'] / btc_monthly_data['SplyCur']

    # Calculating the S/F multiple
    btc_monthly_data['SF_Multiple'] = btc_monthly_data['PriceUSD'] / btc_monthly_data['SF_Predicted_Price']

    # Resampling to daily frequency and forward filling the metrics
    sf_daily_data = btc_monthly_data[['Flow', 'SF', 'SF_Predicted_Market_Value', 'SF_Predicted_Price', 'SF_Multiple']].resample('D').ffill()

    # Adding the new metrics to the original dataframe
    data = data.combine_first(sf_daily_data)

    # Extending the dataset to today's date
    current_date = pd.Timestamp.now().normalize()
    if data.index[-1] < current_date:
        date_range = pd.date_range(start=data.index[-1] + pd.Timedelta(days=1), end=current_date)
        extension_df = pd.DataFrame(index=date_range)
        data = data.append(extension_df).ffill()

    return data

def calculate_statistics(data, start_date):
      # Convert start_date to datetime
      start_date = pd.to_datetime(start_date)

      # Convert index to datetime
      data.index = pd.to_datetime(data.index)

      # Filter data to only include rows after start_date
      data = data[data.index >= start_date]

      # Calculate percentiles and z-scores
      numeric_data = data.select_dtypes(include=[np.number])
      percentiles = numeric_data.apply(lambda x: x.rank(pct=True))
      percentiles.columns = [str(col) + '_percentile' for col in percentiles.columns]
      z_scores = numeric_data.apply(lambda x: (x - x.mean()) / x.std())
      z_scores.columns = [str(col) + '_zscore' for col in z_scores.columns]
      return percentiles, z_scores

def calculate_rolling_correlations(data, periods):
    correlations = {}
    for period in periods:
      correlations[period] = data.rolling(window=period).corr()
    return correlations

def calculate_volatility_tradfi(prices, windows):
      # Calculate daily returns
      returns = prices.pct_change()

      volatilities = pd.DataFrame(index=prices.index)
      for window in windows:
          # Calculate rolling standard deviation of returns
          volatility = returns.rolling(window).std()
          # Annualize volatility
          annualized_volatility = volatility * np.sqrt(252)  # Use 252 trading days for TradFi assets
          volatilities[f'{window}_day_volatility'] = annualized_volatility

      return volatilities

def calculate_volatility_crypto(prices, windows):
      # Calculate daily returns
      returns = prices.pct_change()

      volatilities = pd.DataFrame(index=prices.index)
      for window in windows:
          # Calculate rolling standard deviation of returns
          volatility = returns.rolling(window).std()
          # Annualize volatility
          annualized_volatility = volatility * np.sqrt(365)  # Use 365 trading days for cryptocurrencies
          volatilities[f'{window}_day_volatility'] = annualized_volatility

      return volatilities

def rolling_cagr_for_all_columns(data, years):
      # Convert index to datetime
      data.index = pd.to_datetime(data.index)

      # Calculate percentiles and z-scores
      data = data.select_dtypes(include=[np.number])

      days_per_year = 365  # Hard-coded value
      series_list = []

      for column in data.columns:
          start_value = data[column].shift(int(years * days_per_year))
          end_value = data[column]
          cagr = ((end_value / start_value) ** (1/years)) - 1
          series_list.append(cagr.rename(f"{column}_{years}_Year_CAGR"))

      cagr_data = pd.concat(series_list, axis=1)
      return cagr_data

def calculate_rolling_cagr_for_all_metrics(data):
      cagr_4yr = rolling_cagr_for_all_columns(data, 4)
      cagr_2yr = rolling_cagr_for_all_columns(data, 2)

      return pd.concat([cagr_4yr, cagr_2yr], axis=1)

def calculate_ytd_change(data):
  # Get the first day of the year for each date in the index
  start_of_year = data.index.to_series().apply(lambda x: pd.Timestamp(year=x.year, month=1, day=1))

  # Initialize an empty DataFrame for YTD change
  ytd_change = pd.DataFrame(index=data.index)

  # Get numeric columns
  numeric_cols = data.select_dtypes(include=[np.number]).columns

  # Calculate the YTD change only if the start of the year is in the index
  for date in data.index:
    if start_of_year[date] in data.index:
      ytd_change.loc[date, numeric_cols] = (data.loc[date, numeric_cols] / data.loc[start_of_year[date], numeric_cols] - 1) * 100  # Multiplying by 100 here
    else:
      ytd_change.loc[date, numeric_cols] = np.nan

  # Rename columns
  ytd_change.columns = [f"{col}_YTD_change" for col in ytd_change.columns]
  return ytd_change

def calculate_mtd_change(data):
    # Get the first day of the month for each date in the index
    start_of_month = data.index.to_series().apply(lambda x: pd.Timestamp(year=x.year, month=x.month, day=1))

    # Initialize an empty DataFrame for MTD change
    mtd_change = pd.DataFrame(index=data.index)

    # Get numeric columns
    numeric_cols = data.select_dtypes(include=[np.number]).columns

    # Calculate the MTD change only if the start of the month is in the index
    for date in data.index:
      if start_of_month[date] in data.index:
        mtd_change.loc[date, numeric_cols] = data.loc[date, numeric_cols] / data.loc[start_of_month[date], numeric_cols] - 1
      else:
        mtd_change.loc[date, numeric_cols] = np.nan

    # Rename columns
    mtd_change.columns = [f"{col}_MTD_change" for col in mtd_change.columns]
    return mtd_change

def calculate_time_changes(data, periods):
    changes = pd.DataFrame(index=data.index)
    numeric_data = data.select_dtypes(include=[np.number])  # only include numeric columns
    for period in periods:
      for column in numeric_data.columns:
        changes_temp = numeric_data[column].pct_change(periods=period)
        changes_temp.name = column + f'_{period}_change'
        changes = pd.concat([changes, changes_temp], axis=1)
    return changes

def get_data(tickers, start_date):
    coindata = get_coinmetrics_onchain('btc.csv')
    coindata['time'] = pd.to_datetime(coindata['time'])  # convert to datetime type
    prices = get_price(tickers, start_date)
    marketcaps = get_marketcap(tickers, start_date)
    fear_greed_index = get_fear_and_greed_index()
    data = pd.merge(coindata, prices, on='time', how='left')
    data = pd.merge(data, marketcaps, on='time', how='left')
    data = pd.merge(data, fear_greed_index, on='time', how='left')

    # Set the index to 'time'
    data.set_index('time', inplace=True)

    print("All Raw Data Has Been Fetched & Mergered")
    return data

def calculate_all_changes(data):
    # Define the periods for which we want to calculate changes
    periods = [1,7, 30, 90, 365, 2 * 365, 3 * 365, 4 * 365, 5 * 365]

    # Get the original columns
    original_columns = list(data.columns)

    # Calculate changes for these periods
    changes = calculate_time_changes(data, periods)

    # Calculate YTD changes
    ytd_change = calculate_ytd_change(data[original_columns])

    # Calculate MTD changes
    mtd_change = calculate_mtd_change(data[original_columns])

    # Concatenate all changes at once to avoid DataFrame fragmentation
    changes = pd.concat([changes, ytd_change, mtd_change], axis=1)
    return changes

def run_data_analysis(data, start_date):
    # Calculate changes
    changes = calculate_all_changes(data)

    # Calculate statistics
    percentiles, z_scores = calculate_statistics(data, start_date)

    # Merge changes and statistics into data
    data = pd.concat([data, changes, percentiles, z_scores], axis=1)

    print("Data Analysis Complete")
    return data
  
def get_current_block():
  for _ in range(10):  # Retry up to 10 times
      time.sleep(5)  # Increase the delay to 5 seconds
      response = requests.get('https://blockstream.info/api/blocks/tip/height')

      # Explicitly handling 429 error
      if response.status_code == 429:
          time.sleep(20)  # Wait for 20 seconds before retrying
          continue

      response.raise_for_status()  # This will raise for any other error status
      return response.json()
  else:
      raise Exception("Too many retries due to rate limiting")
    
def get_block_info(block_height):
      time.sleep(1)  # Adding a delay of 1 second
      for _ in range(10):  # Retry up to 10 times
          response = requests.get(f'https://blockstream.info/api/block-height/{block_height}')
          if response.status_code in [429, 502]:
              time.sleep(10)  # Wait for 10 seconds before retrying
              continue
          response.raise_for_status()
          block_hash = response.text.strip()

          # Get the block details for the block hash
          response = requests.get(f'https://blockstream.info/api/block/{block_hash}')
          if response.status_code in [429, 502]:
              time.sleep(10)  # Wait for 10 seconds before retrying
              continue
          response.raise_for_status()
          return response.json()
      else:
          raise Exception("Too many retries")

def get_last_difficulty_change():
      # The block height of a known difficulty adjustment
      KNOWN_DIFFICULTY_ADJUSTMENT_BLOCK = 800352    
      current_block_height = get_current_block()

      # Calculate the number of blocks since the last known difficulty adjustment block
      blocks_since_last_known = current_block_height - KNOWN_DIFFICULTY_ADJUSTMENT_BLOCK

      # Calculate the number of completed difficulty periods
      completed_difficulty_periods = blocks_since_last_known // 2016

      # Calculate the block height of the last difficulty adjustment
      last_difficulty_adjustment_block_height = (completed_difficulty_periods * 2016) + KNOWN_DIFFICULTY_ADJUSTMENT_BLOCK

      # Get the block info for the last difficulty adjustment block
      last_difficulty_adjustment_block = get_block_info(last_difficulty_adjustment_block_height)

      # Subtract 10 minutes from the timestamp to get the approximate timestamp of the last block of the previous interval
      last_difficulty_adjustment_block['timestamp'] -= 10 * 60

      return last_difficulty_adjustment_block

def check_difficulty_change():
      last_difficulty_change_block = get_last_difficulty_change()
      if last_difficulty_change_block is not None:
          # The block height of the last difficulty change
          last_difficulty_change_block_height = last_difficulty_change_block['height']
          # The timestamp of the last difficulty change
          last_difficulty_change_timestamp = last_difficulty_change_block['timestamp']
          # The difficulty of the last difficulty change
          last_difficulty_change_difficulty = last_difficulty_change_block['difficulty']

          # The block height of the previous difficulty change
          previous_difficulty_change_block = get_block_info(last_difficulty_change_block_height - 2016)
          previous_difficulty_change_block_height = previous_difficulty_change_block['height']
          # The timestamp of the previous difficulty change
          previous_difficulty_change_timestamp = previous_difficulty_change_block['timestamp']
          # The difficulty of the previous difficulty change
          previous_difficulty_change_difficulty = previous_difficulty_change_block['difficulty']

          # Calculate difficulty change
          difficulty_change = last_difficulty_change_difficulty - previous_difficulty_change_difficulty

          # Calculate difficulty change percentage
          difficulty_change_percentage = (difficulty_change / previous_difficulty_change_difficulty) * 100

          # Generate the report
          report = {
              'last_difficulty_change': {
                  'block_height': last_difficulty_change_block_height,
                  'timestamp': last_difficulty_change_timestamp,
                  'difficulty': last_difficulty_change_difficulty
              },
              'previous_difficulty_change': {
                  'block_height': previous_difficulty_change_block_height,
                  'timestamp': previous_difficulty_change_timestamp,
                  'difficulty': previous_difficulty_change_difficulty
              },
              'difficulty_change_percentage': difficulty_change_percentage
          }

          # Return the report
          return report

def calculate_metrics_change(difficulty_report, df):
      # Ensure the DataFrame is sorted by date
      df = df.sort_index()

      # Convert the Unix timestamps to datetime format
      last_difficulty_change_time = pd.to_datetime(difficulty_report['last_difficulty_change']['timestamp'], unit='s')
      previous_difficulty_change_time = pd.to_datetime(difficulty_report['previous_difficulty_change']['timestamp'], unit='s')

      # Filter the DataFrame for the time period between the last two difficulty adjustments
      df_filtered = df.loc[previous_difficulty_change_time:last_difficulty_change_time]

      # Calculate the percentage change in metrics
      percentage_changes = ((df_filtered.iloc[-1] - df_filtered.iloc[0]) / df_filtered.iloc[0] * 100).round(2)
      return percentage_changes

def calculate_52_week_high_low(data, current_date):
      high_low = {}

      # Check if current_date is a string, if so convert it to datetime
      if isinstance(current_date, str):
          current_date = datetime.strptime(current_date, '%Y-%m-%d')

      # Calculate the date 52 weeks ago
      start_date = current_date - timedelta(weeks=52)

      # Filter data for the last 52 weeks
      data = data[(data.index >= start_date) & (data.index <= current_date)]

      for column in data.columns:
          high = data[column].max()
          low = data[column].min()
          high_low[column] = {'52_week_high': high, '52_week_low': low}

      return high_low

def create_valuation_data(report_data, valuation_metrics, report_date):
      valuation_data = {}

      # Constants
      number_of_years = 10

      # Retrieve discount rate and future Bitcoin supply from report_data
      discount_rate = report_data.loc[report_date, '^TNX_close'] / 100  # Assuming it is given in percentage
      total_bitcoins_in_circulation = report_data.loc[report_date, 'SplyExpFut10yr']

      current_btc_price = report_data.loc[report_date, 'PriceUSD']

      for metric, targets in valuation_metrics.items():
          if metric != 'market_cap_metrics':
              # Extract the current metric value for the given report date
              current_multiplier = report_data.loc[report_date, metric]

              # Calculate the underlying metric value for that day
              underlying_metric_value = current_btc_price / current_multiplier

              buy_target = targets['buy_target'][0]  # Assuming only one value in the list
              sell_target = targets['sell_target'][0]  # Assuming only one value in the list

              valuation_data[f"{metric}_buy_target"] = buy_target * underlying_metric_value
              valuation_data[f"{metric}_sell_target"] = sell_target * underlying_metric_value
          else:
              # Handle market cap metrics
              for market_cap_metric, details in targets.items():
                  market_cap = report_data.loc[report_date, market_cap_metric]  # Convert billion to billion
                  probabilities = details['probabilities']

                  # Calculate expected and present value for each case (bull, base, bear)
                  for case, prob in probabilities.items():
                      future_value_per_case = market_cap / total_bitcoins_in_circulation
                      present_value_per_case = future_value_per_case / ((1 + discount_rate) ** number_of_years) * prob
                      valuation_data[f"{market_cap_metric}_{case}_future_value"] = future_value_per_case
                      valuation_data[f"{market_cap_metric}_{case}_present_value"] = present_value_per_case

      return valuation_data

def calculate_daily_expected_return(price_series, time_frame, trading_days_in_year):
      daily_returns = price_series.pct_change()
      rolling_avg_return = daily_returns.rolling(window=time_frame).mean() * trading_days_in_year
      return rolling_avg_return

def calculate_standard_deviation_of_returns(price_series, time_frame, trading_days_in_year):
      daily_returns = price_series.pct_change()
      rolling_std_dev = daily_returns.rolling(window=time_frame).std() * (trading_days_in_year ** 0.5)
      return rolling_std_dev

def calculate_sharpe_ratio(expected_return_series, std_dev_series, risk_free_rate_series):
      sharpe_ratio_series = (expected_return_series - risk_free_rate_series) / std_dev_series
      return sharpe_ratio_series

def calculate_daily_sharpe_ratios(data):
      # Define the time frames in trading days
      time_frames = {
          "1_year": {'stock': 252, 'crypto': 365}, 
          "3_year": {'stock': 252 * 3, 'crypto': 365 * 3}, 
          "4_year": {'stock': 252 * 4, 'crypto': 365 * 4}, 
          "2_year": {'stock': 252 * 2, 'crypto': 365 * 2}
      }

      risk_free_rate_series = data['^IRX_close'] / 100  # Convert the annual yield percentages to decimal form

      sharpe_ratios = {}

      for column in data.columns:
          # Skip the column if it's the risk-free rate column
          if column == '^TNX_close':
              continue

          asset_type = 'crypto' if column == 'PriceUSD' else 'stock'

          sharpe_ratios[column] = {}
          for time_frame_label, time_frame_days in time_frames.items():
              expected_return_series = calculate_daily_expected_return(data[column], time_frame_days[asset_type], time_frame_days[asset_type])
              std_dev_series = calculate_standard_deviation_of_returns(data[column], time_frame_days[asset_type], time_frame_days[asset_type])

              sharpe_ratio_series = calculate_sharpe_ratio(expected_return_series, std_dev_series, risk_free_rate_series)
              sharpe_ratios[column][time_frame_label] = sharpe_ratio_series

      # Convert the results to a Pandas DataFrame and return
      sharpe_ratios_df = pd.DataFrame.from_dict({(i, j): sharpe_ratios[i][j] 
                                                 for i in sharpe_ratios.keys() 
                                                 for j in sharpe_ratios[i].keys()}, 
                                                orient='columns')

      return sharpe_ratios_df

def create_btc_correlation_tables(report_date, tickers, correlations_data):
      # Combine all tickers across categories
      all_tickers = [ticker for ticker_list in tickers.values() for ticker in ticker_list]

      # Add the '_close' suffix and include 'PriceUSD'
      ticker_list_with_suffix = ['PriceUSD'] + [f"{ticker}_close" for ticker in all_tickers]

      # Filter the correlation data for the tickers
      filtered_data = correlations_data[ticker_list_with_suffix]

      # Drop NA values
      filtered_data = filtered_data.dropna()

      # Calculate the correlations
      correlations = calculate_rolling_correlations(filtered_data, periods=[7, 30, 90, 365])

      # Extract only the 'PriceUSD' row from each correlation matrix
      btc_correlations = {
          "priceusd_7_days": correlations[7].loc[report_date].loc[['PriceUSD']],
          "priceusd_30_days": correlations[30].loc[report_date].loc[['PriceUSD']],
          "priceusd_90_days": correlations[90].loc[report_date].loc[['PriceUSD']],
          "priceusd_365_days": correlations[365].loc[report_date].loc[['PriceUSD']]
      }

      return btc_correlations

# Compute Drawdown Dataset Function
def compute_drawdowns(data):
    drawdown_periods = [
        ('2011-06-08', '2013-02-28'),
        ('2013-11-29', '2017-03-03'),
        ('2017-12-17', '2020-12-16'),
        ('2021-11-10', pd.to_datetime('today'))
    ]

    drawdown_data = pd.DataFrame()

    for i, period in enumerate(drawdown_periods, 1):
        period_data = data[(data.index >= period[0]) & (data.index <= period[1])]
        period_data = period_data.copy() 
        period_data[f'ath_cycle_{i}'] = period_data['PriceUSD'].cummax()
        period_data[f'drawdown_cycle_{i}'] = (period_data['PriceUSD'] / period_data[f'ath_cycle_{i}'] - 1) * 100
        
        # Calculate 'days_since_ath' from the start of the cycle
        period_start_date = pd.to_datetime(period[0])
        period_data[f'days_since_ath_cycle_{i}'] = (period_data.index - period_start_date).days

        if drawdown_data.empty:
            drawdown_data = period_data[[f'days_since_ath_cycle_{i}', f'drawdown_cycle_{i}']].rename(columns={f'days_since_ath_cycle_{i}': 'days_since_ath', f'drawdown_cycle_{i}': f'drawdown_cycle_{i}'})
        else:
            drawdown_data = pd.concat([drawdown_data, period_data[[f'days_since_ath_cycle_{i}', f'drawdown_cycle_{i}']].rename(columns={f'days_since_ath_cycle_{i}': 'days_since_ath', f'drawdown_cycle_{i}': f'drawdown_cycle_{i}'})])

    return drawdown_data

def compute_cycle_lows(data):
  cycle_periods = [
      ('2010-07-25', '2011-11-18'),
      ('2011-11-18', '2015-01-14'),
      ('2015-01-14', '2018-12-16'),
      ('2018-12-16', '2022-11-20'),
      ('2022-11-20', pd.to_datetime('today'))
  ]
  
  cycle_low_data = pd.DataFrame()
  
  for i, period in enumerate(cycle_periods, 1):
      period_data = data[(data.index >= period[0]) & (data.index <= period[1])]
      period_data = period_data.copy()
  
      # Find the cycle low (minimum price within the period)
      cycle_low_price = period_data['PriceUSD'].min()
      cycle_low_date = period_data['PriceUSD'].idxmin()
  
      # Calculate 'days_since_cycle_low' from the cycle low date
      period_data[f'days_since_cycle_low_{i}'] = (period_data.index - cycle_low_date).days
  
      # Calculate 'return_since_cycle_low' from the cycle low price
      period_data[f'return_since_cycle_low_{i}'] = (period_data['PriceUSD'] / cycle_low_price - 1)
  
      # Select and rename columns to have a consistent name for plotting
      if cycle_low_data.empty:
          cycle_low_data = period_data[[f'days_since_cycle_low_{i}', f'return_since_cycle_low_{i}']].rename(columns={
              f'days_since_cycle_low_{i}': 'days_since_cycle_low',
              f'return_since_cycle_low_{i}': f'return_since_cycle_low_{i}'
          })
      else:
          cycle_low_data = pd.concat([
              cycle_low_data,
              period_data[[f'days_since_cycle_low_{i}', f'return_since_cycle_low_{i}']].rename(columns={
                  f'days_since_cycle_low_{i}': 'days_since_cycle_low',
                  f'return_since_cycle_low_{i}': f'return_since_cycle_low_{i}'
              })
          ])
  
  return cycle_low_data


# Compute Halving Dataset Function
def compute_halving_days(data):
    bitcoin_halvings = [
        ('Genesis Era', '2009-01-03', '2012-11-28'),
        ('2nd Era', '2012-11-28', '2016-07-09'),
        ('3rd Era', '2016-07-09', '2020-05-11'),
        ('4th Era', '2020-05-11', pd.to_datetime('today').strftime('%Y-%m-%d')),
    ]

    halving_data = pd.DataFrame()
    cumulative_days_from_halving = 0

    for i, halving in enumerate(bitcoin_halvings, 1):
        period_data = data[(data.index >= halving[1]) & (data.index <= halving[2])]
        period_data = period_data.copy()
        
        period_data[f'days_since_halving_{i}'] = (period_data.index - pd.to_datetime(halving[1])).days

        period_data[f'return_since_halving_{i}'] = (period_data['PriceUSD'] / period_data.loc[period_data.index == pd.to_datetime(halving[1]), 'PriceUSD'].values[0] - 1) * 100


        if halving_data.empty:
            halving_data = period_data[[f'days_since_halving_{i}', f'return_since_halving_{i}']].rename(columns={f'days_since_halving_{i}': 'days_since_halving', f'return_since_halving_{i}': f'return_since_halving_{i}'})
        else:
            halving_data = pd.concat([halving_data, period_data[[f'days_since_halving_{i}', f'return_since_halving_{i}']].rename(columns={f'days_since_halving_{i}': 'days_since_halving', f'return_since_halving_{i}': f'return_since_halving_{i}'})])

    return halving_data
