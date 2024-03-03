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

def get_miner_data(google_sheet_url):
    try:
      # Constructing the CSV export URL from the Google Sheets URL
      csv_export_url = google_sheet_url.replace('/edit?usp=sharing', '/export?format=csv')
    
      # Loading the data into a pandas DataFrame
      df = pd.read_csv(csv_export_url)
      df['time'] = pd.to_datetime(df['time'])  # Ensure 'time' is datetime type
      print("Miner Data Completed")
      return df
    except Exception as e:
      print("Error loading the Google Sheet:", e)
      return None

def calculate_custom_on_chain_metrics(data):
  # New Metrics Based On Coinmetrics Data
      data['sat_per_dollar'] = 1 / (data['PriceUSD'] /100000000)
      data['mvrv_ratio'] = data['CapMrktCurUSD'] / data['CapRealUSD']
      data['realised_price'] = data['CapRealUSD'] / data['SplyCur']
      data['nupl'] = (data['CapMrktCurUSD'] - data['CapRealUSD']) / data['CapMrktCurUSD']
      data['nvt_price'] = (data['NVTAdj'].rolling(window=365*2).median() * data['TxTfrValAdjUSD']) / data['SplyCur']
      data['nvt_price_adj'] = (data['NVTAdj90'].rolling(window=365).median() * data['TxTfrValAdjUSD']) / data['SplyCur']
      data['nvt_price_multiple'] = data['PriceUSD'] / data['nvt_price']
      data['nvt_price_multiple_ma'] = data['nvt_price_multiple'].rolling(window=14).mean()

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
      data['thermocap_price'] = data['RevAllTimeUSD'] / data['SplyCur']
      data['thermocap_price_multiple_4'] = (4 * data['RevAllTimeUSD']) / data['SplyCur']
      data['thermocap_price_multiple_8'] = (8 * data['RevAllTimeUSD']) / data['SplyCur']
      data['thermocap_price_multiple_16'] = (16 * data['RevAllTimeUSD']) / data['SplyCur']
      data['thermocap_price_multiple_32'] = (32 *data['RevAllTimeUSD']) / data['SplyCur']

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
  new_columns = {}
  for i, row in gold_silver_supply.iterrows():
      metal = row['Metal']
      supply_billion_troy_ounces = row['Supply in Billion Troy Ounces']

      if pd.isna(supply_billion_troy_ounces):
          print(f"Warning: Supply data for {metal} is NaN.")
          continue

      if metal == 'Gold':
          if 'GC=F_close' not in data:
              print("Warning: Gold price data column is missing.")
              continue
          # Use the last available price, forward fill missing values
          price_usd_per_ounce = data['GC=F_close'].ffill()
      elif metal == 'Silver':
          if 'SI=F_close' not in data:
              print("Warning: Silver price data column is missing.")
              continue
          # Use the last available price, forward fill missing values
          price_usd_per_ounce = data['SI=F_close'].ffill()

      metric_name = f'{metal.lower()}_marketcap_billion_usd'
      # Calculate the market cap using the last available price
      market_cap = supply_billion_troy_ounces * price_usd_per_ounce.iloc[-1]
      new_columns[metric_name] = pd.Series(market_cap, index=data.index)

  # Concatenate the new columns to the original data
  data = pd.concat([data, pd.DataFrame(new_columns)], axis=1)
  return data

def calculate_gold_market_cap_breakdown(data, gold_supply_breakdown):
  # Use the latest value of gold market cap
  gold_marketcap_billion_usd = data['gold_marketcap_billion_usd'].iloc[-1]
  
  for i, row in gold_supply_breakdown.iterrows():
      category = row['Gold Supply Breakdown']
      percentage_of_market = row['Percentage Of Market']
      category_marketcap_billion_usd = gold_marketcap_billion_usd * (percentage_of_market / 100.0)
  
      # Create the metric name
      metric_name = 'gold_marketcap_' + category.replace(' ', '_').lower() + '_billion_usd'
  
      # Assign the calculated value to all rows in the new column
      data[metric_name] = category_marketcap_billion_usd
  
  # Explicitly check if the index is a DatetimeIndex; fix if needed
  if not isinstance(data.index, pd.DatetimeIndex):
      try:
          data.index = pd.to_datetime(data.index)
      except ValueError as e:
          print(f"Failed to convert index back to DatetimeIndex: {e}")
  
  return data

def calculate_btc_price_to_surpass_metal_categories(data, gold_supply_breakdown):
  # Ensure 'SplyExpFut10yr' is forward filled to avoid NaN values
  data['SplyExpFut10yr'].ffill(inplace=True)

  # Early return if 'SplyExpFut10yr' for the latest row is zero or NaN to avoid division by zero
  if data['SplyExpFut10yr'].iloc[-1] == 0 or pd.isna(data['SplyExpFut10yr'].iloc[-1]):
      print("Warning: 'SplyExpFut10yr' is zero or NaN for the latest row. Skipping calculations.")
      return data

  new_columns = {}  # Use a dictionary to store new columns

  # Calculating BTC prices required to match or surpass market caps
  gold_marketcap_billion_usd = data['gold_marketcap_billion_usd'].iloc[-1]
  new_columns['gold_marketcap_btc_price'] = gold_marketcap_billion_usd / data['SplyExpFut10yr']

  # Iterating through gold supply breakdown to calculate specific categories
  for i, row in gold_supply_breakdown.iterrows():
      category = row['Gold Supply Breakdown'].replace(' ', '_').lower()
      percentage_of_market = row['Percentage Of Market'] / 100.0
      new_columns[f'gold_{category}_marketcap_btc_price'] = (gold_marketcap_billion_usd * percentage_of_market) / data['SplyExpFut10yr']

  # Silver calculations
  silver_marketcap_billion_usd = data['silver_marketcap_billion_usd'].iloc[-1]
  new_columns['silver_marketcap_btc_price'] = silver_marketcap_billion_usd / data['SplyExpFut10yr']

  # Convert the dictionary to a DataFrame and concatenate it with the original DataFrame
  new_columns_df = pd.DataFrame(new_columns, index=data.index)
  data = pd.concat([data, new_columns_df], axis=1)

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
  # Initialize a dictionary to hold new columns
  new_columns = {}

  # Calculate monthly change in adjusted supply
  new_columns['Monthly_Change'] = data['SplyCur'].diff(periods=31)  # Assuming approximately 30 days per month

  # Annualize the monthly flow
  new_columns['Annual_Flow'] = new_columns['Monthly_Change'] * 12

  # Calculate S2F using adjusted supply
  new_columns['SF'] = data['SplyCur'] / new_columns['Annual_Flow']

  # Applying the linear regression formula
  new_columns['SF_Predicted_Market_Value'] = np.exp(14.6) * new_columns['SF']**3.3

  # Calculating the predicted market price using adjusted supply
  new_columns['SF_Predicted_Price'] = new_columns['SF_Predicted_Market_Value'] / data['SplyCur']

  # Apply a 365-day moving average to the predicted S2F price
  new_columns['SF_Predicted_Price_MA365'] = new_columns['SF_Predicted_Price'].rolling(window=365).mean()

  # Calculating the S/F multiple using the actual price and the 365-day MA of the predicted price
  new_columns['SF_Multiple'] = data['PriceUSD'] / new_columns['SF_Predicted_Price_MA365']

  # Concatenate all new columns to the DataFrame at once
  data = pd.concat([data, pd.DataFrame(new_columns)], axis=1)

  return data
  
def calculate_hayes_production_cost(electricity_cost, miner_efficiency_j_gh, network_hashrate_th_s):
    e_day = electricity_cost * 24 * miner_efficiency_j_gh * network_hashrate_th_s
    return e_day

def calculate_hayes_network_price_per_btc(electricity_cost_per_kwh, miner_efficiency_j_gh, total_network_hashrate_hs, block_reward, mining_difficulty):
    SECONDS_PER_HOUR = 3600
    HOURS_PER_DAY = 24
    SHA_256_CONSTANT = 2**32
    THETA = HOURS_PER_DAY * SHA_256_CONSTANT / SECONDS_PER_HOUR
  
    total_network_hashrate_th_s = total_network_hashrate_hs / 1e12 
    btc_per_day_network_expected = THETA * (block_reward * total_network_hashrate_th_s) / mining_difficulty
    e_day_network = calculate_hayes_production_cost(electricity_cost_per_kwh, miner_efficiency_j_gh, total_network_hashrate_th_s)
    price_per_btc_network_objective = e_day_network / btc_per_day_network_expected if btc_per_day_network_expected != 0 else None
    return price_per_btc_network_objective

def calculate_energy_value(network_hashrate_hs, miner_efficiency_j_gh, annual_growth_rate_percent):
    # Constants for the energy value calculation
    FIAT_FACTOR = 2.0E-15  # Fiat Factor in USD per Joule
    SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60  # Including leap years for accuracy

    network_hashrate_th_s = network_hashrate_hs  # Convert H/s to TH/s
    supply_growth_rate_s = annual_growth_rate_percent / 100 / SECONDS_PER_YEAR
    miner_efficiency_w_th = miner_efficiency_j_gh * 1000  # Convert J/GH to W/TH
    energy_input_watts = network_hashrate_th_s * miner_efficiency_w_th
    energy_value_btc = (energy_input_watts / supply_growth_rate_s) * FIAT_FACTOR
    return energy_value_btc

def calculate_daily_electricity_consumption_kwh_from_hashrate(network_hashrate_th_s, efficiency_j_gh):
  # Convert miner efficiency to J/TH (1 TH = 1000 GH)
  efficiency_j_th = efficiency_j_gh * 1000

  # Calculate total energy consumption in Joules
  total_energy_consumption_joules = network_hashrate_th_s * efficiency_j_th * 3600 * 24

  # Convert Joules to kWh directly
  daily_electricity_consumption_kwh = total_energy_consumption_joules / (1000 * 3600)

  return daily_electricity_consumption_kwh

def calculate_bitcoin_production_cost(daily_electricity_consumption_kwh, electricity_cost_per_kwh, PUE, coinbase_issuance, elec_to_total_cost_ratio):
  # Calculate the total cost of electricity
  total_electricity_cost = daily_electricity_consumption_kwh * electricity_cost_per_kwh * PUE

  # Calculate the Bitcoin electricity price using coinbase issuance
  bitcoin_electricity_price = total_electricity_cost / coinbase_issuance

  # Calculate and return the Bitcoin production cost
  return bitcoin_electricity_price / elec_to_total_cost_ratio

def electric_price_models(data):
  # Constants for energy value calculation
  FIAT_FACTOR = 2.0E-15
  SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60
  ELECTRICITY_COST = 0.05 #per kWh
  PUE = 1.1  # Power Usage Effectiveness
  elec_to_total_cost_ratio = 0.6  # Electricity to Total Cost Ratio
  
  for index, row in data.iterrows():
      # Calculate daily electricity consumption in kWh
      daily_electricity_consumption_kwh = calculate_daily_electricity_consumption_kwh_from_hashrate(row['HashRate'], row['lagged_efficiency_j_gh'])

      # Calculate Bitcoin production cost
      production_cost = calculate_bitcoin_production_cost(
          daily_electricity_consumption_kwh,
          ELECTRICITY_COST, 
          PUE, 
          row['IssContNtv'],  # Coinbase Issuance
          elec_to_total_cost_ratio
      )

      # Update the DataFrame with new values
      data.at[index, 'Bitcoin_Production_Cost'] = production_cost
      data.at[index, 'Electricity_Cost'] = production_cost * elec_to_total_cost_ratio
      
      # Network Price Per BTC Calculation
      network_price = calculate_hayes_network_price_per_btc(
          ELECTRICITY_COST,  # Assumed electricity cost per kWh
          row['lagged_efficiency_j_gh'],
          row['HashRate'],
          row['block_reward'],
          row['DiffLast']
      )
      data.at[index, 'Hayes_Network_Price_Per_BTC'] = network_price
    
      # Energy Value Calculation for Lagged Energy Value
      energy_value = calculate_energy_value(
          row['HashRate'],
          row['lagged_efficiency_j_gh'],
          row['IssContPctAnn']
      )
      data.at[index, 'Lagged_Energy_Value'] = energy_value

      # Now that 'Lagged_Energy_Value' is set, calculate 'Energy_Value_Multiple'
      if energy_value != 0:
          energy_value_multiple = row['PriceUSD'] / energy_value
      else:
          energy_value_multiple = None

      data.at[index, 'Energy_Value_Multiple'] = energy_value_multiple

      # Energy Value Calculation
      energy_value = calculate_energy_value(
          row['HashRate'],
          row['cm_efficiency_j_gh'],
          row['IssContPctAnn']
      )
      data.at[index, 'CM_Energy_Value'] = energy_value  
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
          cagr = ((end_value / start_value) ** (1/years) - 1) * 100  # Multiply by 100 to convert to percentage
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

def calculate_yoy_change(data):
  # Calculate the year-over-year change for each date in the index
  yoy_change = data.pct_change(periods=365) * 100   # Assuming data is daily

  # Rename columns
  yoy_change.columns = [f"{col}_YOY_change" for col in yoy_change.columns]

  return yoy_change

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
  # Placeholder functions to simulate data fetching
  coindata = get_coinmetrics_onchain('btc.csv')
  prices = get_price(tickers, start_date)
  marketcaps = get_marketcap(tickers, start_date)
  fear_greed_index = get_fear_and_greed_index()
  miner_data = get_miner_data("https://docs.google.com/spreadsheets/d/1GXaY6XE2mx5jnCu5uJFejwV95a0gYDJYHtDE0lmkGeA/edit?usp=sharing")

  # Ensure 'time' is datetime and set as index for each DataFrame
  datasets = [coindata, prices, marketcaps, fear_greed_index, miner_data]
  for dataset in datasets:
      dataset['time'] = pd.to_datetime(dataset['time'])
      dataset.set_index('time', inplace=True)

  # Merge datasets using a consistent datetime index
  data = coindata
  for dataset in datasets[1:]:
      data = data.merge(dataset, left_index=True, right_index=True, how='left')

  # Check for and drop duplicates to ensure a clean dataset
  if data.index.duplicated().any():
      print("Warning: Duplicate timestamps found. Dropping duplicates.")
      data = data[~data.index.duplicated()]

  # Forward fill to handle missing values
  data.ffill(inplace=True)

  
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

    # Calculate YoY changes
    yoy_change = calculate_yoy_change(data[original_columns])

    # Concatenate all changes at once to avoid DataFrame fragmentation
    changes = pd.concat([changes, ytd_change, mtd_change,yoy_change], axis=1)
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
  
def compute_drawdowns(data):
  drawdown_periods = [
      ('2011-06-08', '2013-02-28'),
      ('2013-11-29', '2017-03-03'),
      ('2017-12-17', '2020-12-16'),
      ('2021-11-10', pd.to_datetime('today'))
  ]

  drawdown_data = pd.DataFrame()

  for i, period in enumerate(drawdown_periods, 1):
      start_date, end_date = pd.to_datetime(period[0]), pd.to_datetime(period[1])
      period_data = data[(data.index >= start_date) & (data.index <= end_date)].copy()
      period_data[f'ath_cycle_{i}'] = period_data['PriceUSD'].cummax()
      period_data[f'drawdown_cycle_{i}'] = (period_data['PriceUSD'] / period_data[f'ath_cycle_{i}'] - 1) * 100
      period_data['index_as_date'] = pd.to_datetime(period_data.index)
      period_data[f'days_since_ath_cycle_{i}'] = (period_data['index_as_date'] - start_date).dt.days

      selected_columns = [f'days_since_ath_cycle_{i}', f'drawdown_cycle_{i}']
      if drawdown_data.empty:
          drawdown_data = period_data[selected_columns].rename(columns={f'days_since_ath_cycle_{i}': 'days_since_ath', f'drawdown_cycle_{i}': f'drawdown_cycle_{i}'})
      else:
          drawdown_data = pd.concat([drawdown_data, period_data[selected_columns].rename(columns={f'days_since_ath_cycle_{i}': 'days_since_ath', f'drawdown_cycle_{i}': f'drawdown_cycle_{i}'})])

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
      start_date, end_date = pd.to_datetime(period[0]), pd.to_datetime(period[1])
      period_data = data[(data.index >= start_date) & (data.index <= end_date)].copy()
      cycle_low_price = period_data['PriceUSD'].min()
      cycle_low_date = period_data['PriceUSD'].idxmin()
      period_data['index_as_date'] = pd.to_datetime(period_data.index)
      period_data[f'days_since_cycle_low_{i}'] = (period_data['index_as_date'] - cycle_low_date).dt.days
      period_data[f'return_since_cycle_low_{i}'] = (period_data['PriceUSD'] / cycle_low_price - 1) * 100

      selected_columns = [f'days_since_cycle_low_{i}', f'return_since_cycle_low_{i}']
      if cycle_low_data.empty:
          cycle_low_data = period_data[selected_columns].rename(columns={f'days_since_cycle_low_{i}': 'days_since_cycle_low', f'return_since_cycle_low_{i}': f'return_since_cycle_low_{i}'})
      else:
          cycle_low_data = pd.concat([cycle_low_data, period_data[selected_columns].rename(columns={f'days_since_cycle_low_{i}': 'days_since_cycle_low', f'return_since_cycle_low_{i}': f'return_since_cycle_low_{i}'})])

  return cycle_low_data

def compute_halving_days(data):
  bitcoin_halvings = [
      ('Genesis Era', '2009-01-03', '2012-11-28'),
      ('2nd Era', '2012-11-28', '2016-07-09'),
      ('3rd Era', '2016-07-09', '2020-05-11'),
      ('4th Era', '2020-05-11', pd.to_datetime('today').strftime('%Y-%m-%d')),
  ]

  halving_data = pd.DataFrame()

  for i, halving in enumerate(bitcoin_halvings, 1):
      start_date, end_date = pd.to_datetime(halving[1]), pd.to_datetime(halving[2])
      period_data = data[(data.index >= start_date) & (data.index <= end_date)].copy()
      period_data['index_as_date'] = pd.to_datetime(period_data.index)
      period_data[f'days_since_halving_{i}'] = (period_data['index_as_date'] - start_date).dt.days
      period_data[f'return_since_halving_{i}'] = (period_data['PriceUSD'] / period_data.loc[start_date, 'PriceUSD'] - 1) * 100

      selected_columns = [f'days_since_halving_{i}', f'return_since_halving_{i}']
      if halving_data.empty:
          halving_data = period_data[selected_columns].rename(columns={f'days_since_halving_{i}': 'days_since_halving', f'return_since_halving_{i}': f'return_since_halving_{i}'})
      else:
          halving_data = pd.concat([halving_data, period_data[selected_columns].rename(columns={f'days_since_halving_{i}': 'days_since_halving', f'return_since_halving_{i}': f'return_since_halving_{i}'})])

  return halving_data
