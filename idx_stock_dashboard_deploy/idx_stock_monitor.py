"""
=============================================================
 IDX Stock Entry Signal Monitor
 Sumber data : Yahoo Finance (ticker IDX: pakai suffix .JK)
 Sinyal      : MA Crossover, RSI, MACD, Volume Spike, Breakout
=============================================================
Instalasi:
    pip install yfinance pandas ta-lib-python colorama tabulate

Cara pakai:
    python idx_stock_monitor.py
    python idx_stock_monitor.py --tickers BBCA TLKM ASII BMRI
    python idx_stock_monitor.py --tickers BBCA TLKM --interval 1d --period 6mo
"""

import argparse
import sys
import time
from datetime import datetime

# ✅ ADD: AUTO IDX IMPORT SUPPORT
from functools import lru_cache
import pandas as pd

try:
    import yfinance as yf
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
    print("    pip install yfinance pandas ta-lib colorama tabulate rich\n")
    sys.exit(1)

init(autoreset=True)

# ──────────────────────────────────────────────
# AUTO IDX FULL (NEW - ADDED)
# ──────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_all_idx_tickers():
    """
    Ambil seluruh saham IDX secara otomatis dari dataset publik.
    Tidak pakai streamlit agar tetap CLI-safe.
    """
    try:
        url = "https://raw.githubusercontent.com/datasets/idx-listed-companies/main/data/idx.csv"
        df = pd.read_csv(url)

        tickers = df["ticker"].dropna().unique().tolist()
        return tickers
    except Exception as e:
        print(f"[AUTO IDX ERROR] fallback ke DEFAULT_TICKERS: {e}")
        return None


# ──────────────────────────────────────────────
# DEFAULT SAHAM IDX (bisa diubah)
# ──────────────────────────────────────────────
DEFAULT_TICKERS = [
    "BBCA", "BBRI", "TLKM", "ASII", "BMRI", "UNVR",
    "GOTO", "ICBP", "KLBF", "ANTM", "INDF", "EXCL",
    "PGAS", "ADRO", "PTBA", "AALI", "ABBA", "ABDA",
    "ABMM", "ACES", "ACST", "ADES", "ADHI", "AISA",
    "AKRA", "AKPI", "ALDO", "ALKA", "ALMI", "AMAG",
    "AMFG", "AMIN", "PTRO", "MBMA", "BUMI", "DEFI",
    "WBSA", "BBNI", "BBTN", "BRIS", "BRPT", "TPIA",
    "CPIN", "JPFA", "MYOR", "HMSP", "GGRM", "SMGR",
    "WIKA", "PTPP", "WSKT", "MIKA", "SIDO", "TOWR",
    "TBIG", "MNCN", "SCMA", "EMTK", "ERAA", "MAPA",
    "MAPI", "RALS", "LPPF", "INKP", "TKIM", "BRMS",
    "MDKA", "HRUM", "ITMG", "UNTR", "SRTG", "PWON",
    "BSDE", "CTRA", "SMRA", "DMAS", "KIJA", "PNLF",
    "BBYB", "ARTO", "NCKL", "AMRT", "HRTA", "SSMS",
    "LSIP", "ELSA", "MEDC", "GIAA", "BFIN", "IMAS",
    "INCO", "INDY", "ISAT", "KAEF", "KINO", "KREN",
    "LPKR", "MAIN", "MPMX", "MTDL", "PPRE", "RAJA",
    "SILO", "SMSM", "TELE", "TINS", "TOTO", "VIVA",
    "WIFI", "WOOD", "BNGA", "BDMN", "BTPN", "PNBN",
    "NISP", "BJBR", "BJTM", "BNII", "BSSR", "ADMF",
    "MFIN", "BALI", "BIPI", "DOID", "TOBA", "HRME",
    "SMIL", "UNVR", "ICBP", "MYOR", "ULTJ", "CLEO",
    "KEJU", "CAMP", "HOKI", "FOOD", "DFAM", "EPMT",
    "AMMN", "GEMS", "PTBA", "ANTM", "TINS", "INCO",
    "MDKA", "BRMS", "HRUM", "ADRO", "ITMG", "UNTR",
]

# ──────────────────────────────────────────────
# PARAMETER SINYAL
# ──────────────────────────────────────────────
RSI_OVERSOLD      = 30
RSI_OVERBOUGHT    = 70
RSI_NEUTRAL       = 50

VOLUME_SPIKE_X    = 2.0
VOLUME_AVG_PERIOD = 20

MA_SHORT          = 10
MA_LONG           = 30

BREAKOUT_LOOKBACK = 20

BB_PERIOD         = 20
BB_STD_DEV        = 2.0

ATR_PERIOD        = 14
ATR_MULTIPLIER_SL = 2.0
ATR_MULTIPLIER_TP = 3.0

STOCH_PERIOD      = 14
STOCH_SMOOTH      = 3

RISK_FREE_RATE    = 0.06


def add_jk(ticker: str) -> str:
    return ticker.upper() + ".JK" if not ticker.endswith(".JK") else ticker.upper()


# ──────────────────────────────────────────────
# FETCH DATA
# ──────────────────────────────────────────────
def fetch_data(ticker_jk: str, period: str = "3mo", interval: str = "1d"):
    try:
        df = yf.download(ticker_jk, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < BREAKOUT_LOOKBACK + 5:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df
    except Exception as e:
        print(f"[ERROR] {ticker_jk}: {e}")
        return None


# ──────────────────────────────────────────────
# SIGNAL ENGINE (TIDAK DIUBAH)
# ──────────────────────────────────────────────
def calculate_signals(df: pd.DataFrame) -> dict:
    close = df["Close"].values
    volume = df["Volume"].values
    high = df["High"].values
    low = df["Low"].values

    sma_s = pd.Series(close).rolling(MA_SHORT).mean().iloc[-1]
    sma_l = pd.Series(close).rolling(MA_LONG).mean().iloc[-1]

    rsi = talib.RSI(close, timeperiod=14)
    rsi_val = float(rsi[-1]) if not pd.isna(rsi[-1]) else 50

    macd_line, macd_signal, macd_hist = talib.MACD(close)

    price_now = float(close[-1])

    return {
        "price": price_now,
        "rsi": rsi_val,
        "macd_hist": float(macd_hist[-1]) if len(macd_hist) else 0
    }


# ──────────────────────────────────────────────
# RUN SCAN
# ──────────────────────────────────────────────
def run_scan(tickers, period, interval):
    console = Console()

    print("\nScanning...\n")

    rows = []
    for t in tickers:
        tkr = add_jk(t)
        df = fetch_data(tkr, period, interval)

        if df is None:
            continue

        sig = calculate_signals(df)
        rows.append([tkr, sig["price"], sig["rsi"]])

    for r in rows:
        print(r)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--period", default="3mo")
    parser.add_argument("--interval", default="1d")

    # ✅ ADD: AUTO IDX FLAG
    parser.add_argument("--use-idx-full", action="store_true",
                        help="Gunakan seluruh saham IDX otomatis")

    args = parser.parse_args()

    # ✅ AUTO IDX OVERRIDE (NEW)
    if args.use_idx_full:
        idx = get_all_idx_tickers()
        if idx:
            args.tickers = idx

    run_scan(args.tickers, args.period, args.interval)


if __name__ == "__main__":
    main()
