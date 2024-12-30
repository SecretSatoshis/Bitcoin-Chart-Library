import datetime
import pandas as pd

# TradFi Data
# TradFi Data
tickers = {
    "stocks": [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "NVDA",
        "TSLA",
        "META",
        "BRK-A",
        "BRK-B",
        "TSM",
        "V",
        "JPM",
        "PYPL",
        "GS",
        "COIN",
        "SQ",
        "MSTR",
        "MARA",
        "RIOT",
    ],
    "etfs": [
        "BITQ",
        "CLOU",
        "ARKK",
        "XLK",
        "QQQ",
        "IUIT.L",
        "VTI",
        "TLT",
        "LQD",
        "JNK",
        "GLD",
        "XLF",
        "XLRE",
        "SHY",
        "XLE",
        "FANG.AX",
        "SPY",
        "IEMG",
        "AGG",
        "WGMI",
        "VXUS",
    ],
    "indices": ["^GSPC", "^VIX", "^IXIC", "^TNX", "^TYX", "^FVX", "^IRX", "^BCOM"],
    "commodities": ["GC=F", "CL=F", "SI=F"],
    "forex": [
        "DX=F",
        "AUDUSD=X",
        "CHFUSD=X",
        "CNYUSD=X",
        "EURUSD=X",
        "GBPUSD=X",
        "HKDUSD=X",
        "INRUSD=X",
        "JPYUSD=X",
        "RUBUSD=X",
    ],
}

# Start date for TradFi Data
market_data_start_date = "2010-01-01"

# Fiat Money Supply M0 Data
fiat_money_data_top10 = pd.DataFrame(
    {
        "Country": [
            "United States",
            "China",
            "Eurozone",
            "Japan",
            "United Kingdom",
            "Switzerland",
            "India",
            "Australia",
            "Russia",
            "Hong Kong",
            "Global Fiat Supply",
        ],
        "US Dollar Trillion": [
            5.73,
            5.11,
            5.19,
            4.20,
            1.09,
            0.58,
            0.56,
            0.24,
            0.30,
            0.25,
            26.1,
        ],
    }
)

# Gold And Silver Supply Data
gold_silver_supply = pd.DataFrame(
    {
        "Metal": ["Gold", "Silver"],
        "Supply in Billion Troy Ounces": [6100000000, 30900000000],
    }
)

# Gold Market Supply Breakdown
gold_supply_breakdown = pd.DataFrame(
    {
        "Gold Supply Breakdown": [
            "Jewellery",
            "Private Investment",
            "Official Country Holdings",
            "Other",
        ],
        "Percentage Of Market": [47.00, 22.00, 17.00, 14.00],
    }
)

# Just stock tickers for marketcap calculation
stock_tickers = tickers["stocks"]

# Get today's date
today = datetime.date.today()

# Get yesterday's date
yesterday = today - datetime.timedelta(days=1)

# Creat report data and convert to pandas.Timestamp
report_date = pd.Timestamp(yesterday)

# On-Chain Metrics to create moving averages of for data smoothing
moving_avg_metrics = [
    "HashRate",
    "AdrActCnt",
    "TxCnt",
    "TxTfrValAdjUSD",
    "TxTfrValMeanUSD",
    "TxTfrValMedUSD",
    "FeeMeanUSD",
    "FeeMeanNtv",
    "IssContNtv",
    "RevUSD",
    "nvt_price",
    "nvt_price_adj",
]

# Define report data and fields
filter_data_columns = {
    "Report_Metrics": [
        "SplyCur",
        "SplyExpFut10yr",
        "7_day_ma_IssContNtv",
        "365_day_ma_IssContNtv",
        "TxCnt",
        "7_day_ma_TxCnt",
        "365_day_ma_TxCnt",
        "HashRate",
        "7_day_ma_HashRate",
        "365_day_ma_HashRate",
        "PriceUSD",
        "50_day_ma_priceUSD",
        "200_day_ma_priceUSD",
        "200_day_multiple",
        "200_week_ma_priceUSD",
        "TxTfrValAdjUSD",
        "7_day_ma_TxTfrValAdjUSD",
        "365_day_ma_TxTfrValAdjUSD",
        "RevUSD",
        "AdrActCnt",
        "7_day_ma_priceUSD",
        "30_day_ma_AdrActCnt",
        "365_day_ma_AdrActCnt",
        "7_day_ma_TxTfrValMeanUSD",
        "FeeTotUSD",
        "thermocap_price",
        "thermocap_multiple",
        "thermocap_price_multiple_4",
        "thermocap_price_multiple_8",
        "thermocap_price_multiple_16",
        "thermocap_price_multiple_32",
        "nvt_price",
        "nvt_price_adj",
        "nvt_price_multiple",
        "30_day_ma_nvt_price",
        "nvt_price_multiple_ma",
        "365_day_ma_nvt_price",
        "NVTAdj",
        "NVTAdj90",
        "NVTAdjFF",
        "realised_price",
        "VelCur1yr",
        "supply_pct_1_year_plus",
        "mvrv_ratio",
        "realizedcap_multiple_3",
        "realizedcap_multiple_5",
        "nupl",
        "AAPL_close",
        "CapMrktCurUSD",
        "^IXIC_close",
        "RevHashRateUSD",
        "^GSPC_close",
        "XLF_close",
        "XLRE_close",
        "GC=F_close",
        "SI=F_close",
        "DX=F_close",
        "SHY_close",
        "TLT_close",
        "^TNX_close",
        "^TYX_close",
        "^FVX_close",
        "^IRX_close",
        "XLE_close",
        "BITQ_close",
        "FANG.AX_close",
        "AAPL_mc_btc_price",
        "AAPL_MarketCap",
        "AUDUSD=X_close",
        "CHFUSD=X_close",
        "CNYUSD=X_close",
        "EURUSD=X_close",
        "GBPUSD=X_close",
        "HKDUSD=X_close",
        "INRUSD=X_close",
        "JPYUSD=X_close",
        "RUBUSD=X_close",
        "silver_marketcap_billion_usd",
        "gold_marketcap_billion_usd",
        "30_day_ma_IssContNtv",
        "30_day_ma_TxCnt",
        "30_day_ma_HashRate",
        "30_day_ma_TxTfrValAdjUSD",
        "30_day_ma_RevUSD",
        "365_day_ma_RevUSD",
        "30_day_ma_TxTfrValMeanUSD",
        "30_day_ma_TxTfrValMedUSD",
        "AdrBalUSD1MCnt",
        "AdrBalUSD10MCnt",
        "AdrBalUSD10KCnt",
        "AdrBalUSD1KCnt",
        "AdrBalUSD10Cnt",
        "AdrBalUSD1Cnt",
        "AdrBalCnt",
        "SplyAct1d",
        "SplyAct30d",
        "SplyAct90d",
        "SplyAct180d",
        "SplyAct1yr",
        "SplyAct3yr",
        "SplyAct4yr",
        "SplyAct2yr",
        "SplyAct5yr",
        "SplyAct10yr",
        "SplyFF",
        "CapMVRVCur",
        "liquid_supply",
        "illiquid_supply",
        "SplyMiner0HopAllNtv",
        "SplyMiner1HopAllNtv",
        "TxTfrValAdjNtv",
        "United_Kingdom_btc_price",
        "United_Kingdom_cap",
        "United_States_btc_price",
        "United_States_cap",
        "Global_Fiat_Supply_btc_price",
        "SF_Predicted_Price",
        "SF_Multiple",
        "China_btc_price",
        "Eurozone_btc_price",
        "Japan_btc_price",
        "Switzerland_btc_price",
        "India_btc_price",
        "Australia_btc_price",
        "Russia_btc_price",
        "MSFT_mc_btc_price",
        "GOOGL_mc_btc_price",
        "NVDA_mc_btc_price",
        "AMZN_mc_btc_price",
        "V_mc_btc_price",
        "TSLA_mc_btc_price",
        "JPM_mc_btc_price",
        "PYPL_mc_btc_price",
        "GS_mc_btc_price",
        "META_mc_btc_price",
        "gold_marketcap_btc_price",
        "silver_marketcap_btc_price",
        "gold_jewellery_marketcap_btc_price",
        "gold_private_investment_marketcap_btc_price",
        "gold_official_country_holdings_marketcap_btc_price",
        "gold_other_marketcap_btc_price",
        "sat_per_dollar",
        "Lagged_Energy_Value",
        "Hayes_Network_Price_Per_BTC",
        "Electricity_Cost",
        "Bitcoin_Production_Cost",
        "CM_Energy_Value",
        "Energy_Value_Multiple",
        "SF_Predicted_Price_MA365",
        "SPY_close",   # S&P 500 ETF
        "QQQ_close",   # Nasdaq-100 ETF
        "VTI_close",   # US Total Stock Market ETF
        "VXUS_close",  # International Stock ETF
        "XLK_close",   # Technology Sector ETF
        "GLD_close",   # Gold ETF
        "AGG_close",   # Aggregate Bond ETF
        "^BCOM_close", # Bloomberg Commodity Index
        "MSTR_close",  # MicroStrategy
        "SQ_close",    # Block
        "COIN_close",  # Coinbase
        "WGMI_close",  # Bitcoin Miners ETF
    ]
}

# First Halving Date Start Stats Calculation
stats_start_date = "2012-11-28"

# Timeframes to calculate volatitlity for
volatility_windows = [30, 90, 180, 365]
