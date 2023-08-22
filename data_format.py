import pandas as pd
import requests
from io import StringIO
from yahoo_fin import stock_info as si

# Function to fetch data from the CoinMetrics API
def gather_data_from_coinmetrics(endpoint):
    url = f'https://coinmetrics.io/newdata/{endpoint}'
    response = requests.get(url)
    data = pd.read_csv(StringIO(response.text), low_memory=False)
    data['time'] = pd.to_datetime(data['time'])
    return data

# Function to fetch data from the Yahoo Finance API
def get_stock_prices(tickers, start_date):
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

# Function to fetch data from the Yahoo Finance API
def get_market_caps(tickers, start_date):
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

# Function to gather data from all APIs and merge the resulting DataFrames
def gather_data(tickers, start_date):
    coindata = gather_data_from_coinmetrics('btc.csv')
    coindata['time'] = pd.to_datetime(coindata['time'])  # convert to datetime type
    stock_prices = get_stock_prices(tickers, start_date)
    market_caps = get_market_caps(tickers, start_date)
    data = pd.merge(coindata, stock_prices, on='time', how='left')
    data = pd.merge(data, market_caps, on='time', how='left')
    return data
  
# Function to create custom metrics based on imported data
def create_report_data(data):
  # New Metrics Based On Coinmetrics Data
  data['mvrv_ratio'] = data['CapMrktCurUSD'] / data['CapRealUSD']
  data['realised_price'] = data['CapRealUSD'] / data['SplyCur']
  data['nupl'] = (data['CapMrktCurUSD'] - data['CapRealUSD']) / data['CapMrktCurUSD']
  data['nvt_price'] = (data['NVTAdj90'] * data['TxTfrValAdjUSD']) / data['SplyCur']
  data['nvt_price_FF'] = (data['NVTAdjFF90'] * data['TxTfrValAdjUSD']) / data['SplyCur']

  # Price Moving Averages
  data['7_day_ma_priceUSD'] = data['PriceUSD'].rolling(window=7).mean()
  data['50_day_ma_priceUSD'] = data['PriceUSD'].rolling(window=50).mean()
  data['100_day_ma_priceUSD'] = data['PriceUSD'].rolling(window=100).mean()
  data['200_day_ma_priceUSD'] = data['PriceUSD'].rolling(window=200).mean()
  data['200_week_ma_priceUSD'] = data['PriceUSD'].rolling(window=200 * 7).mean()

  # Metric Moving Averages 7 Day
  data['7_day_ma_HashRate'] = data['HashRate'].rolling(window=7).mean()
  data['7_day_ma_AdrActCnt'] = data['AdrActCnt'].rolling(window=7).mean()
  data['7_day_ma_TxCnt'] = data['TxCnt'].rolling(window=7).mean()
  data['7_day_ma_TxTfrValAdjUSD'] = data['TxTfrValAdjUSD'].rolling(window=7).mean()
  data['7_day_ma_TxTfrValMeanUSD'] = data['TxTfrValMeanUSD'].rolling(window=7).mean()
  data['7_day_ma_FeeMeanUSD'] = data['FeeMeanUSD'].rolling(window=7).mean()
  data['7_day_ma_FeeMeanNtv'] = data['FeeMeanNtv'].rolling(window=7).mean()
  data['7_day_ma_IssContNtv'] = data['IssContNtv'].rolling(window=7).mean()
  data['7_day_ma_MinerRevenue'] = data['RevUSD'].rolling(window=7).mean()
  data['7_day_ma_nvt_price'] = data['nvt_price'].rolling(window=7).mean()
  data['7_day_ma_nvt_price'] = data['nvt_price_FF'].rolling(window=7).mean()
  
  # Metric Moving Averages 30 Day
  data['30_day_ma_HashRate'] = data['HashRate'].rolling(window=30).mean()
  data['30_day_ma_AdrActCnt'] = data['AdrActCnt'].rolling(window=30).mean()
  data['30_day_ma_TxCnt'] = data['TxCnt'].rolling(window=30).mean()
  data['30_day_ma_TxTfrValAdjUSD'] = data['TxTfrValAdjUSD'].rolling(window=30).mean()
  data['30_day_ma_TxTfrValMeanUSD'] = data['TxTfrValMeanUSD'].rolling(window=30).mean()
  data['30_day_ma_TxTfrValMedUSD'] = data['TxTfrValMedUSD'].rolling(window=30).mean()
  data['30_day_ma_FeeMeanUSD'] = data['FeeMeanUSD'].rolling(window=30).mean()
  data['30_day_ma_FeeMeanNtv'] = data['FeeMeanNtv'].rolling(window=30).mean()
  data['30_day_ma_IssContNtv'] = data['IssContNtv'].rolling(window=30).mean()
  data['30_day_ma_MinerRevenue'] = data['RevUSD'].rolling(window=30).mean()
  data['30_day_ma_nvt_price'] = data['nvt_price'].rolling(window=30).mean()
  data['30_day_ma_nvt_price'] = data['nvt_price_FF'].rolling(window=30).mean()

  # Metric Moving Averages 365 Day
  data['365_day_ma_HashRate'] = data['HashRate'].rolling(window=365).mean()
  data['365_day_ma_AdrActCnt'] = data['AdrActCnt'].rolling(window=365).mean()
  data['365_day_ma_TxCnt'] = data['TxCnt'].rolling(window=365).mean()
  data['365_day_ma_TxTfrValAdjUSD'] = data['TxTfrValAdjUSD'].rolling(window=365).mean()
  data['365_day_ma_FeeMeanUSD'] = data['FeeMeanUSD'].rolling(window=365).mean()
  data['365_day_ma_FeeMeanNtv'] = data['FeeMeanNtv'].rolling(window=365).mean()
  data['365_day_ma_IssContNtv'] = data['IssContNtv'].rolling(window=365).mean()
  data['365_day_ma_MinerRevenue'] = data['RevUSD'].rolling(window=365).mean()
  data['365_day_ma_nvt_price'] = data['nvt_price'].rolling(window=365).mean()
  data['365_day_ma_nvt_price'] = data['nvt_price_FF'].rolling(window=365).mean()

  # Price Multiple
  data['200_day_multiple'] = data['PriceUSD'] / data['200_day_ma_priceUSD']

  # Thermocap Multiple
  data['thermocap_multiple'] = data['CapMrktCurUSD'] / data['RevAllTimeUSD']
  data['thermocap_multiple_4'] = (4 * data['RevAllTimeUSD']) / data['SplyCur']
  data['thermocap_multiple_8'] = (8 * data['RevAllTimeUSD']) / data['SplyCur']
  data['thermocap_multiple_16'] = (16 * data['RevAllTimeUSD']) / data['SplyCur']
  data['thermocap_multiple_32'] = (32 * data['RevAllTimeUSD']) / data['SplyCur']

  # Realized Cap Multiple
  data['realizedcap_multiple_3'] = (3 * data['CapRealUSD']) / data['SplyCur']
  data['realizedcap_multiple_5'] = (5 * data['CapRealUSD']) / data['SplyCur']
  data['realizedcap_multiple_7'] = (7 * data['CapRealUSD']) / data['SplyCur']

  # 1+ Year Supply % 
  data['supply_pct_1_year_plus'] = (100 - data['SplyActPct1yr'])
  data['illiquid_supply'] = ((data['supply_pct_1_year_plus'] / 100) * data['SplyCur'])
  data['liquid_supply'] = (data['SplyCur'] - data['illiquid_supply'])
  
  # Fiat Money Supply M0 Data
  fiat_money_data_top10 = pd.DataFrame({
    'Country': ['United States', 'China', 'Eurozone', 'Japan', 'United Kingdom', 'Switzerland', 'India', 'Australia', 'Russia', 'Hong Kong','Global Fiat Supply'],
    'US Dollar Trillion': [5.41, 4.81, 6.16, 4.50, 1.16, 0.71, 0.50, 0.36, 0.35, 0.25,26.77]
  })
    
  # New metrics: price of Bitcoin needed to surpass each country's M0 money supply
  for i, row in fiat_money_data_top10.iterrows():
        country = row['Country']
        fiat_supply_usd_trillion = row['US Dollar Trillion']

        # Convert the fiat supply from trillions to just units
        fiat_supply_usd = fiat_supply_usd_trillion * 1e12

        # Compute the price of Bitcoin needed to surpass this country's M0 money supply
        # This is simply the fiat supply divided by the current Bitcoin supply
        metric_name = country.replace(" ", "_") + '_btc_price'
        data[metric_name] = fiat_supply_usd / data['SplyExpFut10yr']

  #Gold And Silver Supply Data
  gold_silver_supply = pd.DataFrame({
    "Metal": ["Gold", "Silver"],
    "Supply in Billion Troy Ounces": [5630000000, 28400000000]})
  
  # New metrics: market cap of Gold and Silver
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

  #Gold Market Supply Breakdown
  gold_supply_breakdown = pd.DataFrame({
    "Gold Supply Breakdown": ["Jewellery", "Private Investment", "Official Country Holdings", "Other"],
    "Percentage Of Market": [47.00, 22.00, 17.00, 14.00]})
 
  # Compute the gold market cap breakdown
  gold_marketcap_billion_usd = data['gold_marketcap_billion_usd'].iloc[-1]  # get the latest value
  for i, row in gold_supply_breakdown.iterrows():
        category = row['Gold Supply Breakdown']
        percentage_of_market = row['Percentage Of Market']

        # Compute the market cap for this category
        category_marketcap_billion_usd = gold_marketcap_billion_usd * (percentage_of_market / 100.0)

        # Add a new metric to the data
        metric_name = 'gold_marketcap_' + category.replace(' ', '_').lower() + '_billion_usd'
        data[metric_name] = category_marketcap_billion_usd  

  # BTC Price For Surpassing Gold Marketcap Levels
  data['gold_mc_btc_price'] = data['gold_marketcap_billion_usd'] / data['SplyExpFut10yr']
  data['silver_mc_btc_price'] = data['silver_marketcap_billion_usd'] / data['SplyExpFut10yr']
  data['gold_jewellery_mc_btc_price'] = data['gold_marketcap_jewellery_billion_usd'] / data['SplyExpFut10yr']
  data['gold_private_investment_mc_btc_price'] = data['gold_marketcap_private_investment_billion_usd'] / data['SplyExpFut10yr']
  data['gold_country_holdings_mc_btc_price'] = data['gold_marketcap_official_country_holdings_billion_usd'] / data['SplyExpFut10yr']
  data['gold_other_mc_btc_price'] = data['gold_marketcap_other_billion_usd'] / data['SplyExpFut10yr']

  # BTC Price For Surpassing Various Stock Market Cap Levels
  data['AAPL_mc_btc_price'] = data['AAPL_MarketCap'] / data['SplyExpFut10yr']
  data['MSFT_mc_btc_price'] = data['MSFT_MarketCap'] / data['SplyExpFut10yr']
  data['GOOGL_mc_btc_price'] = data['GOOGL_MarketCap'] / data['SplyExpFut10yr']
  data['AMZN_mc_btc_price'] = data['AMZN_MarketCap'] / data['SplyExpFut10yr']
  data['NVDA_mc_btc_price'] = data['NVDA_MarketCap'] / data['SplyExpFut10yr']
  data['TSLA_mc_btc_price'] = data['TSLA_MarketCap'] / data['SplyExpFut10yr']
  data['META_mc_btc_price'] = data['META_MarketCap'] / data['SplyExpFut10yr']
  data['BRK-A_mc_btc_price'] = data['BRK-A_MarketCap'] / data['SplyExpFut10yr']
  data['BRK-B_mc_btc_price'] = data['BRK-B_MarketCap'] / data['SplyExpFut10yr']
  data['TSM_mc_btc_price'] = data['TSM_MarketCap'] / data['SplyExpFut10yr']
  data['V_mc_btc_price'] = data['V_MarketCap'] / data['SplyExpFut10yr']
  data['JPM_mc_btc_price'] = data['JPM_MarketCap'] / data['SplyExpFut10yr']
  data['PYPL_mc_btc_price'] = data['PYPL_MarketCap'] / data['SplyExpFut10yr']
  data['GS_mc_btc_price'] = data['GS_MarketCap'] / data['SplyExpFut10yr']

  # Convert the time column to datetime format
  selected_metrics = data.copy()
  selected_metrics['time'] = pd.to_datetime(selected_metrics['time'])
  
  # Write data headers to a file
  with open('data_output.txt', 'w') as file:
      file.write(', '.join(selected_metrics.columns))
  
  return selected_metrics

# Compute Drawdown Dataset Function
def compute_drawdowns(data):
    drawdown_periods = [
        ('2011-06-08', '2013-12-19'),
        ('2013-12-04', '2017-01-03'),
        ('2017-12-16', '2020-12-03'),
        ('2021-11-08', pd.to_datetime('today'))
    ]

    drawdown_data = pd.DataFrame()

    for i, period in enumerate(drawdown_periods, 1):
        period_data = data[(data['time'] >= period[0]) & (data['time'] <= period[1])]
        period_data = period_data.copy() 
        period_data[f'ath_cycle_{i}'] = period_data['PriceUSD'].cummax()
        period_data[f'drawdown_cycle_{i}'] = (period_data['PriceUSD'] / period_data[f'ath_cycle_{i}'] - 1) * 100
        
        # Calculate 'days_since_ath' from the start of the cycle
        period_start_date = pd.to_datetime(period[0])
        period_data[f'days_since_ath_cycle_{i}'] = (period_data['time'] - period_start_date).dt.days

        if drawdown_data.empty:
            drawdown_data = period_data[[f'days_since_ath_cycle_{i}', f'drawdown_cycle_{i}']].rename(columns={f'days_since_ath_cycle_{i}': 'days_since_ath', f'drawdown_cycle_{i}': f'drawdown_cycle_{i}'})
        else:
            drawdown_data = pd.concat([drawdown_data, period_data[[f'days_since_ath_cycle_{i}', f'drawdown_cycle_{i}']].rename(columns={f'days_since_ath_cycle_{i}': 'days_since_ath', f'drawdown_cycle_{i}': f'drawdown_cycle_{i}'})])

    return drawdown_data

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
        period_data = data[(data['time'] >= halving[1]) & (data['time'] <= halving[2])]
        period_data = period_data.copy()
        
        period_data[f'days_since_halving_{i}'] = (period_data['time'] - pd.to_datetime(halving[1])).dt.days
        period_data[f'return_since_halving_{i}'] = (period_data['PriceUSD'] / period_data.loc[period_data['time'] == pd.to_datetime(halving[1]), 'PriceUSD'].values[0] - 1) * 100

        if halving_data.empty:
            halving_data = period_data[[f'days_since_halving_{i}', f'return_since_halving_{i}']].rename(columns={f'days_since_halving_{i}': 'days_since_halving', f'return_since_halving_{i}': f'return_since_halving_{i}'})
        else:
            halving_data = pd.concat([halving_data, period_data[[f'days_since_halving_{i}', f'return_since_halving_{i}']].rename(columns={f'days_since_halving_{i}': 'days_since_halving', f'return_since_halving_{i}': f'return_since_halving_{i}'})])

    return halving_data

# Data Defintions
start_date = '2010-08-18'
end_date = pd.to_datetime('today')
tickers = {
    'stocks': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-A', 'BRK-B', 'TSM', 'V', 'JPM', 'PYPL', 'GS'],
    'commodities': ['GC=F', 'CL=F', 'SI=F'],
}