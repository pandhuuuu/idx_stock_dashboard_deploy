"""
=============================================================
 IDX Stock Entry Signal Monitor — IMPROVED (PDF-Based)
=============================================================
 Improvements based on research paper:
   "Technical indicator empowered intelligent strategies to
    predict stock trading signals" (Saud & Shakya, 2024)

 Added:
   - DMI  : +DI / -DI / ADX  (14-period, ADX > 25 = strong trend)
   - KST  : SMA10(ROC10)×1 + SMA10(ROC15)×2 +
             SMA10(ROC20)×3 + SMA15(ROC30)×4  → Signal = SMA9(KST)
   - MACD : proper LINE-CROSS detection (not just histogram sign)
   - ADX filter on SMA cross (reduces false signals in weak trends)
   - ATR-based dynamic SL/TP  (replaces fixed 2%/3%)
   - Signal label  : BUY / SELL / HOLD  based on combined score
=============================================================
"""

import argparse
import time
import os
from functools import lru_cache

import numpy as np
import pandas as pd
import yfinance as yf
import talib
import requests

from colorama import init, Fore, Style
from tabulate import tabulate
from dotenv import load_dotenv

init(autoreset=True)

# ──────────────────────────────────────────────
# LOAD ENV
# ──────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

if not API_KEY:
    print("⚠️  WARNING: API KEY tidak ditemukan di .env")

# ──────────────────────────────────────────────
# DEFAULT TICKERS
# ──────────────────────────────────────────────
DEFAULT_TICKERS = [
    "BBCA","BBRI","BMRI","BRIS","EMAS","ANTM","MDKA","BRMS","ARCI","WBSA",
    "DEFI","ENRG","PGAS","ADRO","PTBA","AALI","ADMR","ADHI","AKRA",
    "PTRO","MBMA","BUMI","BRPT","MEDC","CDIA","JPFA","MYOR","HMSP",
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
# FETCH DATA  (HYBRID: yfinance → Alpha Vantage)
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# KST  (Know Sure Thing — computed manually)
# Paper eq.(3): Saud & Shakya 2024
#   KST = SMA10(ROC10)×1 + SMA10(ROC15)×2
#         + SMA10(ROC20)×3 + SMA15(ROC30)×4
#   Signal = SMA9(KST)
# ──────────────────────────────────────────────
def _sma(series: np.ndarray, period: int) -> np.ndarray:
    return pd.Series(series).rolling(period).mean().values

def calculate_kst(close: np.ndarray):
    """Return (kst_array, signal_array) aligned to close length."""
    roc10 = talib.ROC(close, timeperiod=10)
    roc15 = talib.ROC(close, timeperiod=15)
    roc20 = talib.ROC(close, timeperiod=20)
    roc30 = talib.ROC(close, timeperiod=30)

    kst = (
        _sma(roc10, 10) * 1 +
        _sma(roc15, 10) * 2 +
        _sma(roc20, 10) * 3 +
        _sma(roc30, 15) * 4
    )
    signal = _sma(kst, 9)
    return kst, signal


# ──────────────────────────────────────────────
# SIGNAL ENGINE
# ──────────────────────────────────────────────
def calculate_signals(df: pd.DataFrame) -> dict:
    """
    Returns a dict with all signal data.
    Keys kept backward-compatible; new keys added.
    """
    high  = df["High"].values.astype(float)
    low   = df["Low"].values.astype(float)
    close = df["Close"].values.astype(float)

    if len(close) < 35:          # not enough bars for KST
        return None

    price_now = float(close[-1])

    # ── SMA crossover (short 10 / long 30) ──
    sma_s = pd.Series(close).rolling(10).mean().values
    sma_l = pd.Series(close).rolling(30).mean().values
    sma_bull = bool(sma_s[-1] > sma_l[-1])

    # ── RSI (14) ── [PDF: RSI(14), OB=70, OS=30]
    rsi_arr = talib.RSI(close, timeperiod=14)
    rsi_val = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0

    # ── MACD — proper crossover detection ──
    # Paper: buy when MACD LINE crosses ABOVE Signal Line
    macd_line, macd_sig, macd_hist = talib.MACD(close)
    # crossover = previous bar MACD < signal  AND  current bar MACD > signal
    if (not np.isnan(macd_line[-2]) and not np.isnan(macd_sig[-2]) and
            not np.isnan(macd_line[-1]) and not np.isnan(macd_sig[-1])):
        macd_cross_up   = (macd_line[-2] < macd_sig[-2]) and (macd_line[-1] > macd_sig[-1])
        macd_cross_down = (macd_line[-2] > macd_sig[-2]) and (macd_line[-1] < macd_sig[-1])
        macd_bull       = macd_line[-1] > macd_sig[-1]   # current position (no cross)
    else:
        macd_cross_up = macd_cross_down = False
        macd_bull = False

    # ── DMI (+DI / -DI / ADX)  [Paper eq.(2), 14-period] ──
    plus_di  = talib.PLUS_DI(high, low, close, timeperiod=14)
    minus_di = talib.MINUS_DI(high, low, close, timeperiod=14)
    adx_arr  = talib.ADX(high, low, close, timeperiod=14)
    adx_val  = float(adx_arr[-1]) if not np.isnan(adx_arr[-1]) else 0.0
    pdi      = float(plus_di[-1])  if not np.isnan(plus_di[-1])  else 0.0
    mdi      = float(minus_di[-1]) if not np.isnan(minus_di[-1]) else 0.0
    # Strong trend gate: ADX > 25 (paper threshold)
    trend_strong = adx_val > 25
    dmi_bull  = bool(pdi > mdi and trend_strong)
    dmi_bear  = bool(mdi > pdi and trend_strong)

    # ── KST  [Paper eq.(3)] ──
    kst_arr, kst_sig_arr = calculate_kst(close)
    kst_val  = float(kst_arr[-1])     if not np.isnan(kst_arr[-1])     else 0.0
    kst_s    = float(kst_sig_arr[-1]) if not np.isnan(kst_sig_arr[-1]) else 0.0
    kst_prev = float(kst_arr[-2])     if not np.isnan(kst_arr[-2])     else kst_val
    kst_s_p  = float(kst_sig_arr[-2]) if not np.isnan(kst_sig_arr[-2]) else kst_s
    kst_cross_up   = (kst_prev < kst_s_p) and (kst_val > kst_s)   # bullish crossover
    kst_cross_down = (kst_prev > kst_s_p) and (kst_val < kst_s)   # bearish crossover
    kst_bull = kst_val > kst_s and kst_val > 0   # above signal & positive = bullish

    # ── ATR-based dynamic SL / TP ──
    atr_arr = talib.ATR(high, low, close, timeperiod=14)
    atr_val = float(atr_arr[-1]) if not np.isnan(atr_arr[-1]) else price_now * 0.02
    suggested_sl = price_now - 1.5 * atr_val    # 1.5× ATR stop
    suggested_tp = price_now + 2.5 * atr_val    # 2.5× ATR target  (R:R ≈ 1.67)
    risk_reward  = abs(suggested_tp - price_now) / max(abs(price_now - suggested_sl), 1e-6)

    # ── SCORING  (paper-informed weights) ──
    # MACD is "safest and most effective" → crossover scores 2; position scores 1
    # DMI with ADX>25 = reliable trend confirmation → scores 2
    # KST crossover → scores 1; position → scores 0.5
    # RSI OS/OB → classic 2 pts; SMA cross → 1 pt
    bull_score = 0.0
    bear_score = 0.0

    # SMA  (filtered by ADX for false-signal reduction)
    if sma_bull and trend_strong:
        bull_score += 1
    elif not sma_bull and trend_strong:
        bear_score += 1

    # RSI
    if rsi_val < 30:
        bull_score += 2
    elif rsi_val > 70:
        bear_score += 2

    # MACD  (crossover = higher weight; just position = lower weight)
    if macd_cross_up:
        bull_score += 2
    elif macd_cross_down:
        bear_score += 2
    elif macd_bull:
        bull_score += 1
    else:
        bear_score += 1

    # DMI
    if dmi_bull:
        bull_score += 2
    elif dmi_bear:
        bear_score += 2

    # KST
    if kst_cross_up:
        bull_score += 1
    elif kst_cross_down:
        bear_score += 1
    elif kst_bull:
        bull_score += 0.5
    else:
        bear_score += 0.5

    bull_score = round(bull_score, 1)
    bear_score = round(bear_score, 1)
    total_max  = bull_score + bear_score
    confidence = round(max(bull_score, bear_score) / total_max * 100, 1) if total_max else 50.0

    # ── Signal label ──
    margin = bull_score - bear_score
    if margin >= 2:
        signal = "BUY"
    elif margin <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        # ── backward-compatible keys ──
        "price":         price_now,
        "rsi":           round(rsi_val, 2),
        "bull_score":    bull_score,
        "bear_score":    bear_score,
        "confidence":    confidence,
        "suggested_sl":  round(suggested_sl, 2),
        "suggested_tp":  round(suggested_tp, 2),
        "risk_reward":   round(risk_reward, 2),
        # ── new keys from PDF indicators ──
        "signal":        signal,
        "adx":           round(adx_val, 2),
        "plus_di":       round(pdi, 2),
        "minus_di":      round(mdi, 2),
        "kst":           round(kst_val, 4),
        "kst_signal":    round(kst_s,   4),
        "macd_cross":    "↑" if macd_cross_up else ("↓" if macd_cross_down else "-"),
        "kst_cross":     "↑" if kst_cross_up  else ("↓" if kst_cross_down  else "-"),
    }


# ──────────────────────────────────────────────
# SCANNER
# ──────────────────────────────────────────────
_SIGNAL_COLOR = {"BUY": Fore.GREEN, "SELL": Fore.RED, "HOLD": Fore.YELLOW}

def run_scan(tickers, period, interval):
    print("\n📊 SCANNING...\n")
    rows = []

    for t in tickers:
        df = fetch_data(add_jk(t), period, interval)
        if df is None:
            continue

        sig = calculate_signals(df)
        if sig is None:
            continue

        color = _SIGNAL_COLOR.get(sig["signal"], "")
        rows.append([
            t,
            round(sig["price"], 0),
            round(sig["rsi"],   2),
            sig["bull_score"],
            sig["bear_score"],
            f"{color}{sig['signal']}{Style.RESET_ALL}",
            round(sig["adx"],   2),
            sig["macd_cross"],
            sig["kst_cross"],
            round(sig["suggested_sl"], 0),
            round(sig["suggested_tp"], 0),
            round(sig["risk_reward"],  2),
        ])

    headers = [
        "Ticker", "Price", "RSI",
        "Bull", "Bear", "Signal",
        "ADX", "MACD×", "KST×",
        "SL", "TP", "R:R",
    ]
    print(tabulate(rows, headers=headers, tablefmt="simple"))


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers",      nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--period",       default="3mo")
    parser.add_argument("--interval",     default="1d")
    parser.add_argument("--use-idx-full", action="store_true")
    args = parser.parse_args()

    if args.use_idx_full:
        idx = get_all_idx_tickers()
        if idx:
            args.tickers = idx

    run_scan(args.tickers, args.period, args.interval)


if __name__ == "__main__":
    main()
