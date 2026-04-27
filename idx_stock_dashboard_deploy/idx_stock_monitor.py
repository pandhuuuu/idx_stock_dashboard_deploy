"""
=============================================================
 IDX Stock Entry Signal Monitor (FINAL HYBRID + ENV)
=============================================================
"""

import argparse
import time
import os
from functools import lru_cache

import pandas as pd
import yfinance as yf
import talib
import requests

from colorama import init
from tabulate import tabulate
from dotenv import load_dotenv

init(autoreset=True)

# ──────────────────────────────────────────────
# LOAD ENV
# ──────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

if not API_KEY:
    print("⚠️ WARNING: API KEY tidak ditemukan di .env")

# ──────────────────────────────────────────────
# DEFAULT TICKERS
# ──────────────────────────────────────────────
DEFAULT_TICKERS = [
    "BBCA","BBRI","TLKM","ASII","BMRI","UNVR","GOTO","ICBP","KLBF","ANTM",
    "INDF","EXCL","PGAS","ADRO","PTBA","AALI","ABMM","ACES","ADHI","AKRA",
    "PTRO","MBMA","BUMI","BBNI","BBTN","BRIS","CPIN","JPFA","MYOR","HMSP",
]

# ──────────────────────────────────────────────
# AUTO IDX
# ──────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_all_idx_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/idx-listed-companies/main/data/idx.csv"
        df = pd.read_csv(url)
        return df["ticker"].dropna().unique().tolist()
    except Exception as e:
        print(f"[AUTO IDX ERROR]: {e}")
        return None


# ──────────────────────────────────────────────
# UTIL
# ──────────────────────────────────────────────
def add_jk(ticker: str) -> str:
    return ticker.upper() + ".JK" if not ticker.endswith(".JK") else ticker.upper()


# ──────────────────────────────────────────────
# FETCH DATA (HYBRID)
# ──────────────────────────────────────────────
@lru_cache(maxsize=128)
def fetch_data(ticker_jk: str, period="3mo", interval="1d"):

    # ───────────────
    # 1. YFINANCE (PRIMARY)
    # ───────────────
    try:
        df = yf.download(
            ticker_jk,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True
        )

        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df

    except Exception as e:
        print(f"[YF ERROR] {ticker_jk}: {e}")

    # ───────────────
    # 2. ALPHA VANTAGE (FALLBACK)
    # ───────────────
    if not API_KEY:
        return None

    try:
        symbol = ticker_jk.replace(".JK", "")

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY
        }

        res = requests.get(url, params=params)
        data = res.json()

        if "Time Series (Daily)" not in data:
            print(f"[AV FAIL] {ticker_jk}")
            return None

        df = pd.DataFrame.from_dict(
            data["Time Series (Daily)"], orient="index"
        )

        df = df.rename(columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close",
            "5. volume": "Volume"
        })

        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.astype(float)

        print(f"[FALLBACK AV] {ticker_jk}")

        time.sleep(12)  # anti rate limit

        return df

    except Exception as e:
        print(f"[AV ERROR] {ticker_jk}: {e}")
        return None


# ──────────────────────────────────────────────
# SIGNAL ENGINE
# ──────────────────────────────────────────────
def calculate_signals(df: pd.DataFrame) -> dict:
    close = df["Close"].values

    sma_s = pd.Series(close).rolling(10).mean().iloc[-1]
    sma_l = pd.Series(close).rolling(30).mean().iloc[-1]

    rsi = talib.RSI(close, timeperiod=14)
    rsi_val = float(rsi[-1]) if not pd.isna(rsi[-1]) else 50

    macd_line, macd_signal, macd_hist = talib.MACD(close)

    price_now = float(close[-1])

    bull_score = 0
    bear_score = 0

    if sma_s > sma_l:
        bull_score += 1
    else:
        bear_score += 1

    if rsi_val < 30:
        bull_score += 2
    elif rsi_val > 70:
        bear_score += 2

    if len(macd_hist) > 0:
        if macd_hist[-1] > 0:
            bull_score += 1
        else:
            bear_score += 1

    suggested_sl = price_now * 0.98
    suggested_tp = price_now * 1.03

    risk_reward = abs(suggested_tp - price_now) / max(abs(price_now - suggested_sl), 1)

    return {
        "price": price_now,
        "rsi": rsi_val,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "confidence": max(bull_score, bear_score),
        "suggested_sl": suggested_sl,
        "suggested_tp": suggested_tp,
        "risk_reward": risk_reward,
    }


# ──────────────────────────────────────────────
# SCANNER
# ──────────────────────────────────────────────
def run_scan(tickers, period, interval):
    print("\n📊 SCANNING...\n")

    rows = []

    for t in tickers:
        df = fetch_data(add_jk(t), period, interval)

        if df is None:
            continue

        sig = calculate_signals(df)

        rows.append([
            t,
            round(sig["price"], 2),
            round(sig["rsi"], 2),
            sig["bull_score"],
            sig["bear_score"]
        ])

    print(tabulate(rows, headers=["Ticker","Price","RSI","Bull","Bear"]))


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--period", default="3mo")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--use-idx-full", action="store_true")

    args = parser.parse_args()

    if args.use_idx_full:
        idx = get_all_idx_tickers()
        if idx:
            args.tickers = idx

    run_scan(args.tickers, args.period, args.interval)


if __name__ == "__main__":
    main()
