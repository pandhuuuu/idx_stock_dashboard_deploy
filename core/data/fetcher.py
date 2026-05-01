import time
import requests
import pandas as pd
import yfinance as yf
from functools import lru_cache

from config import config

@lru_cache(maxsize=128)
def fetch_data(ticker_jk: str, period="3mo", interval="1d"):
    # ── 1. YFINANCE (PRIMARY) ──
    try:
        df = yf.download(
            ticker_jk,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
    except Exception as e:
        print(f"[YF ERROR] {ticker_jk}: {e}")

    # ── 2. ALPHA VANTAGE (FALLBACK) ──
    if not config.ALPHA_VANTAGE_API_KEY:
        return None

    try:
        symbol = ticker_jk.replace(".JK", "")
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": config.ALPHA_VANTAGE_API_KEY,
        }
        res = requests.get(url, params=params)
        data = res.json()

        if "Time Series (Daily)" not in data:
            print(f"[AV FAIL] {ticker_jk}")
            return None

        df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
        df = df.rename(columns={
            "1. open": "Open", "2. high": "High",
            "3. low": "Low",  "4. close": "Close", "5. volume": "Volume",
        })
        df.index = pd.to_datetime(df.index)
        df = df.sort_index().astype(float)
        print(f"[FALLBACK AV] {ticker_jk}")
        time.sleep(12)
        return df

    except Exception as e:
        print(f"[AV ERROR] {ticker_jk}: {e}")
        return None
