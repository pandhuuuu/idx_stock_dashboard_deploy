"""
=============================================================
IDX Stock Entry Signal Monitor
Sumber data : Yahoo Finance (ticker IDX: pakai suffix .JK)

Sinyal :
- MA Crossover
- RSI
- MACD
- Volume Spike
- Breakout
- Bollinger Bands
- ATR Risk Management
=============================================================

Instalasi:
pip install yfinance pandas ta-lib-python colorama tabulate rich

Cara pakai:
python idx_stock_monitor.py
python idx_stock_monitor.py --tickers BBCA TLKM ASII BMRI
python idx_stock_monitor.py --tickers BBCA TLKM --interval 1d --period 6mo
"""

import argparse
import sys
import time
from datetime import datetime

try:
    import yfinance as yf
    import pandas as pd
    import talib
    from colorama import init, Fore, Style
    from tabulate import tabulate
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.layout import Layout
    from rich.align import Align
except ImportError:
    print("\n[!] Modul belum terinstall. Jalankan:\n")
    print("pip install yfinance pandas ta-lib-python colorama tabulate rich\n")
    sys.exit(1)

init(autoreset=True)

# ──────────────────────────────────────────────
# DEFAULT TICKERS
# ──────────────────────────────────────────────
DEFAULT_TICKERS = [
    "BBCA", "BBRI", "TLKM", "ASII", "BMRI", "UNVR", "GOTO", "ICBP",
    "KLBF", "ANTM", "INDF", "EXCL", "PGAS", "ADRO", "PTBA", "AALI",
    "ABBA", "ABDA", "ABMM", "ACES", "ACST", "ADES", "ADHI", "AISA",
    "AKRA", "AMFG"
]

# ──────────────────────────────────────────────
# PARAMETER
# ──────────────────────────────────────────────
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_NEUTRAL = 50

VOLUME_SPIKE_X = 2.0
VOLUME_AVG_PERIOD = 20

MA_SHORT = 10
MA_LONG = 30

BREAKOUT_LOOKBACK = 20

BB_PERIOD = 20
BB_STD_DEV = 2.0

ATR_PERIOD = 14
ATR_MULTIPLIER_SL = 2.0
ATR_MULTIPLIER_TP = 3.0

STOCH_PERIOD = 14
STOCH_SMOOTH = 3


# ──────────────────────────────────────────────
def add_jk(ticker: str) -> str:
    return ticker.upper() + ".JK" if not ticker.endswith(".JK") else ticker.upper()


# ──────────────────────────────────────────────
def fetch_data(ticker_jk: str, period="3mo", interval="1d"):
    try:
        df = yf.download(
            ticker_jk,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True
        )

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df

    except Exception as e:
        print(f"[ERROR] {ticker_jk}: {e}")
        return None


# ──────────────────────────────────────────────
def calculate_signals(df: pd.DataFrame) -> dict:
    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    volume = df["Volume"].values

    price_now = float(close[-1])

    # MA
    sma_s = pd.Series(close).rolling(MA_SHORT).mean().iloc[-1]
    sma_l = pd.Series(close).rolling(MA_LONG).mean().iloc[-1]

    ma_cross_up = sma_s > sma_l

    # RSI
    rsi = talib.RSI(close, 14)
    rsi_val = float(rsi[-1]) if not pd.isna(rsi[-1]) else 50

    # MACD
    macd_line, macd_signal, macd_hist = talib.MACD(close, 12, 26, 9)

    # ATR
    atr = talib.ATR(high, low, close, ATR_PERIOD)
    atr_val = float(atr[-1]) if not pd.isna(atr[-1]) else 0

    sl = price_now - (ATR_MULTIPLIER_SL * atr_val)
    tp = price_now + (ATR_MULTIPLIER_TP * atr_val)

    # Volume
    vol_avg = pd.Series(volume).rolling(VOLUME_AVG_PERIOD).mean().iloc[-1]
    rvol = volume[-1] / vol_avg if vol_avg > 0 else 0

    # Breakout
    recent_high = high[-(BREAKOUT_LOOKBACK + 1):-1].max()
    breakout = price_now > recent_high

    # Score sederhana
    bull = 0
    bear = 0

    if ma_cross_up:
        bull += 1
    else:
        bear += 1

    if rsi_val < RSI_OVERSOLD:
        bull += 1
    elif rsi_val > RSI_OVERBOUGHT:
        bear += 1

    if rvol > VOLUME_SPIKE_X:
        bull += 1

    if breakout:
        bull += 1

    return {
        "price": price_now,
        "rsi": rsi_val,
        "rvol": rvol,
        "atr": atr_val,
        "sl": sl,
        "tp": tp,
        "bull": bull,
        "bear": bear
    }


# ──────────────────────────────────────────────
def run_scan(tickers, period, interval):
    console = Console()

    console.print(Panel("📊 IDX STOCK MONITOR", style="bold cyan"))

    table = Table()
    table.add_column("Saham")
    table.add_column("Harga")
    table.add_column("RSI")
    table.add_column("RVOL")
    table.add_column("Signal")

    for t in tickers:
        tk = add_jk(t)
        df = fetch_data(tk, period, interval)

        if df is None:
            table.add_row(t, "-", "-", "-", "NO DATA")
            continue

        sig = calculate_signals(df)

        direction = "BUY" if sig["bull"] > sig["bear"] else "SELL"

        table.add_row(
            t,
            f"{sig['price']:.0f}",
            f"{sig['rsi']:.1f}",
            f"{sig['rvol']:.1f}x",
            direction
        )

    console.print(table)


# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--period", default="3mo")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--loop", type=int, default=0)

    args = parser.parse_args()

    if args.loop > 0:
        while True:
            run_scan(args.tickers, args.period, args.interval)
            time.sleep(args.loop * 60)
    else:
        run_scan(args.tickers, args.period, args.interval)


if __name__ == "__main__":
    main()
