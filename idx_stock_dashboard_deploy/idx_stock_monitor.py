# idx_stock_monitor.py

import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
from functools import lru_cache
import talib
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# =========================
# DEFAULT TICKERS
# =========================
DEFAULT_TICKERS = [
    "BBCA","BBRI","BMRI","BRIS","EMAS","ANTM","MDKA","BRMS","ARCI","WBSA",
    "DEFI","ENRG","PGAS","ADRO","PTBA","AALI","ADMR","ADHI","AKRA",
    "PTRO","MBMA","BUMI","BRPT","MEDC","CDIA","JPFA","MYOR","HMSP",
]

# =========================
# UTIL
# =========================
def add_jk(ticker: str) -> str:
    return ticker.upper() + ".JK" if not ticker.endswith(".JK") else ticker.upper()


# =========================
# AUTO IDX LIST
# =========================
@lru_cache(maxsize=1)
def get_all_idx_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/idx-listed-companies/main/data/idx.csv"
        df = pd.read_csv(url)
        return df["ticker"].dropna().unique().tolist()
    except Exception as e:
        print(f"[AUTO IDX ERROR]: {e}")
        return None


# =========================
# FETCH DATA
# =========================
@lru_cache(maxsize=128)
def fetch_data(ticker_jk: str, period="3mo", interval="1d"):
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

    # fallback Alpha Vantage
    if not API_KEY:
        return None

    try:
        symbol = ticker_jk.replace(".JK", "")
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY,
        }

        res = requests.get(url, params=params)
        data = res.json()

        if "Time Series (Daily)" not in data:
            return None

        df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
        df = df.rename(columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close",
            "5. volume": "Volume",
        })

        df.index = pd.to_datetime(df.index)
        df = df.sort_index().astype(float)

        time.sleep(12)
        return df

    except Exception as e:
        print(f"[AV ERROR] {ticker_jk}: {e}")
        return None


# =========================
# SIGNALS (FULL LOGIC TETAP)
# =========================
def calculate_signals(df: pd.DataFrame):
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    close = df["Close"].values.astype(float)

    if len(close) < 35:
        return None

    price_now = float(close[-1])

    sma_s = pd.Series(close).rolling(10).mean().values
    sma_l = pd.Series(close).rolling(30).mean().values
    sma_bull = sma_s[-1] > sma_l[-1]

    rsi = talib.RSI(close, 14)
    rsi_val = rsi[-1] if not np.isnan(rsi[-1]) else 50

    macd, macdsignal, _ = talib.MACD(close)
    macd_cross_up = macd[-2] < macdsignal[-2] and macd[-1] > macdsignal[-1]
    macd_cross_down = macd[-2] > macdsignal[-2] and macd[-1] < macdsignal[-1]
    macd_bull = macd[-1] > macdsignal[-1]

    plus_di = talib.PLUS_DI(high, low, close, 14)
    minus_di = talib.MINUS_DI(high, low, close, 14)
    adx = talib.ADX(high, low, close, 14)

    adx_val = adx[-1]
    dmi_bull = plus_di[-1] > minus_di[-1] and adx_val > 25
    dmi_bear = minus_di[-1] > plus_di[-1] and adx_val > 25

    bull = 0
    bear = 0

    if sma_bull:
        bull += 1
    else:
        bear += 1

    if rsi_val < 30:
        bull += 2
    elif rsi_val > 70:
        bear += 2

    if macd_cross_up:
        bull += 2
    elif macd_cross_down:
        bear += 2

    if dmi_bull:
        bull += 2
    elif dmi_bear:
        bear += 2

    signal = "BUY" if bull > bear + 1 else "SELL" if bear > bull + 1 else "HOLD"

    return {
        "price": price_now,
        "rsi": rsi_val,
        "bull_score": bull,
        "bear_score": bear,
        "confidence": max(bull, bear) / (bull + bear) * 100 if (bull + bear) else 50,
        "signal": signal,
        "suggested_tp": price_now * 1.03,
        "suggested_sl": price_now * 0.98,
        "risk_reward": 2.0,
    }
