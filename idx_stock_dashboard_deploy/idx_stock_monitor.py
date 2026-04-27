"""
=============================================================
 IDX Stock Entry Signal Monitor
=============================================================
"""

import argparse
import sys
import time
from datetime import datetime
from functools import lru_cache
import pandas as pd
import yfinance as yf
import talib

# optional CLI UI
from colorama import init
from tabulate import tabulate

init(autoreset=True)


# ──────────────────────────────────────────────
# AUTO IDX FULL
# ──────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_all_idx_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/idx-listed-companies/main/data/idx.csv"
        df = pd.read_csv(url)
        return df["ticker"].dropna().unique().tolist()
    except Exception as e:
        print(f"[AUTO IDX ERROR] fallback default: {e}")
        return None


# ──────────────────────────────────────────────
# DEFAULT TICKERS
# ──────────────────────────────────────────────
DEFAULT_TICKERS = [
    "BBCA","BBRI","TLKM","ASII","BMRI","UNVR","GOTO","ICBP","KLBF","ANTM",
    "INDF","EXCL","PGAS","ADRO","PTBA","AALI","ABMM","ACES","ADHI","AKRA",
    "PTRO","MBMA","BUMI","BBNI","BBTN","BRIS","CPIN","JPFA","MYOR","HMSP",
]


# ──────────────────────────────────────────────
# UTIL
# ──────────────────────────────────────────────
def add_jk(ticker: str) -> str:
    return ticker.upper() + ".JK" if not ticker.endswith(".JK") else ticker.upper()


# ──────────────────────────────────────────────
# FETCH DATA
# ──────────────────────────────────────────────
def fetch_data(ticker_jk: str, period="3mo", interval="1d"):
    try:
        df = yf.download(ticker_jk, period=period, interval=interval,
                         progress=False, auto_adjust=True)

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df
    except Exception as e:
        print(f"[ERROR] {ticker_jk}: {e}")
        return None


# ──────────────────────────────────────────────
# SIGNAL ENGINE (FIXED + STREAMLIT COMPATIBLE)
# ──────────────────────────────────────────────
def calculate_signals(df: pd.DataFrame) -> dict:
    close = df["Close"].values

    sma_s = pd.Series(close).rolling(10).mean().iloc[-1]
    sma_l = pd.Series(close).rolling(30).mean().iloc[-1]

    rsi = talib.RSI(close, timeperiod=14)
    rsi_val = float(rsi[-1]) if not pd.isna(rsi[-1]) else 50

    macd_line, macd_signal, macd_hist = talib.MACD(close)

    price_now = float(close[-1])

    # ─────────────────────────────
    # SIMPLE SCORING ENGINE (SAFE)
    # ─────────────────────────────
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

    # ─────────────────────────────
    # RISK MANAGEMENT (SAFE DEFAULT)
    # ─────────────────────────────
    suggested_sl = price_now * 0.98
    suggested_tp = price_now * 1.03

    risk_reward = abs(suggested_tp - price_now) / max(abs(price_now - suggested_sl), 1)

    return {
        "price": price_now,
        "rsi": rsi_val,

        # STREAMLIT REQUIRED
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
            sig["price"],
            sig["rsi"],
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
