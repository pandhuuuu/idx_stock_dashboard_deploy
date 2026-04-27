"""
=============================================================
IDX Stock Entry Signal Monitor
Sumber data : Yahoo Finance (ticker IDX: pakai suffix .JK)

Sinyal : MA Crossover, RSI, MACD, Volume Spike, Breakout
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
    print("\n[!] Modul belum terinstall. Jalankan perintah berikut:\n")
    print(" pip install yfinance pandas ta-lib-python colorama tabulate rich\n")
    sys.exit(1)

init(autoreset=True)

# ──────────────────────────────────────────────
# DEFAULT SAHAM IDX
# ──────────────────────────────────────────────
DEFAULT_TICKERS = [
    "BBCA", "BBBRI", "TLKM", "ASII", "BMRI", "UNVR", "GOTO", "ICBP", "KLBF",
    "ANTM", "INDF", "EXCL", "PGAS", "ADRO", "PTBA", "AALI", "ABBA", "ABDA",
    "ABMM", "ACES", "ACST", "ADES", "ADHI", "AISA", "AKKU", "AKPI", "AKRA",
    "AKSI", "ALDO", "ALKA", "ALMI", "ALTO", "AMAG", "AMFG", "AMIN",
]

# ──────────────────────────────────────────────
# PARAMETER SINYAL
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
def fetch_data(ticker_jk: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame | None:
    try:
        df = yf.download(
            ticker_jk,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True
        )

        if df.empty or len(df) < BREAKOUT_LOOKBACK + 5:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df

    except Exception as e:
        print(f"{Fore.RED}[ERROR] {ticker_jk}: {e}{Style.RESET_ALL}")
        return None


# ──────────────────────────────────────────────
def calculate_signals(df: pd.DataFrame) -> dict:
    close = df["Close"].values
    volume = df["Volume"].values
    high = df["High"].values
    low = df["Low"].values

    sma_s = pd.Series(close).rolling(MA_SHORT).mean().iloc[-1]
    sma_l = pd.Series(close).rolling(MA_LONG).mean().iloc[-1]

    ma_cross_up = (
        close[-1] > sma_s
        and close[-2] <= pd.Series(close).rolling(MA_SHORT).mean().iloc[-2]
        and sma_s > sma_l
    )

    ma_cross_dn = (
        close[-1] < sma_s
        and close[-2] >= pd.Series(close).rolling(MA_SHORT).mean().iloc[-2]
        and sma_s < sma_l
    )

    rsi = talib.RSI(close, timeperiod=14)
    rsi_val = float(rsi[-1]) if not pd.isna(rsi[-1]) else 50

    macd_line, macd_signal, macd_hist = talib.MACD(
        close, fastperiod=12, slowperiod=26, signalperiod=9
    )

    k_percent, d_percent = talib.STOCH(
        high, low, close,
        fastk_period=STOCH_PERIOD,
        slowk_period=STOCH_SMOOTH,
        slowd_period=STOCH_SMOOTH
    )

    bb_upper, bb_middle, bb_lower = talib.BBANDS(
        close, timeperiod=BB_PERIOD,
        nbdevup=BB_STD_DEV,
        nbdevdn=BB_STD_DEV
    )

    price_now = float(close[-1])

    atr = talib.ATR(high, low, close, timeperiod=ATR_PERIOD)
    atr_val = float(atr[-1]) if not pd.isna(atr[-1]) else 0

    suggested_sl = price_now - (ATR_MULTIPLIER_SL * atr_val)
    suggested_tp = price_now + (ATR_MULTIPLIER_TP * atr_val)

    vol_avg = pd.Series(volume).rolling(VOLUME_AVG_PERIOD).mean().iloc[-1]
    vol_now = float(volume[-1])
    rvol = vol_now / vol_avg if vol_avg > 0 else 0

    recent_high = high[-(BREAKOUT_LOOKBACK + 1):-1].max()
    breakout_up = price_now > recent_high

    bull_score = 0
    bear_score = 0
    signals_detail = []

    if ma_cross_up:
        bull_score += 2.0
        signals_detail.append("MA Cross UP")
    if ma_cross_dn:
        bear_score += 2.0
        signals_detail.append("MA Cross DN")

    if rsi_val < RSI_OVERSOLD:
        bull_score += 1.5
    if rsi_val > RSI_OVERBOUGHT:
        bear_score += 1.5

    if rvol >= VOLUME_SPIKE_X:
        bull_score += 1.0

    if breakout_up:
        bull_score += 1.5

    max_score = max(bull_score, bear_score) if max(bull_score, bear_score) > 0 else 1

    return {
        "price": price_now,
        "rsi": rsi_val,
        "rvol": rvol,
        "atr": atr_val,
        "suggested_sl": suggested_sl,
        "suggested_tp": suggested_tp,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "signals": signals_detail,
        "confidence": max_score
    }


# ──────────────────────────────────────────────
def format_row(ticker: str, sig: dict) -> list:
    direction = "BUY" if sig["bull_score"] > sig["bear_score"] else "SELL"

    return [
        ticker.replace(".JK", ""),
        f"{sig['price']:.0f}",
        f"{sig['rsi']:.1f}",
        f"{sig['rvol']:.1f}x",
        direction,
        ", ".join(sig["signals"])[:50]
    ]


# ──────────────────────────────────────────────
def run_scan(tickers: list[str], period: str, interval: str):
    console = Console()

    console.print(Panel("IDX STOCK ENTRY SIGNAL MONITOR", style="cyan"))

    table = Table()
    table.add_column("Saham")
    table.add_column("Harga")
    table.add_column("RSI")
    table.add_column("Volume")
    table.add_column("Signal")
    table.add_column("Detail")

    for t in tickers:
        tk = add_jk(t)
        df = fetch_data(tk, period, interval)

        if df is None:
            table.add_row(t, "-", "-", "-", "NO DATA", "-")
            continue

        sig = calculate_signals(df)
        table.add_row(*format_row(tk, sig))

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
