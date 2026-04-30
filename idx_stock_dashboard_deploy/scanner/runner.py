import argparse
from colorama import init, Fore, Style
from tabulate import tabulate

from core.utils.helpers import add_jk
from core.data.ticker import get_all_idx_tickers, DEFAULT_TICKERS
from core.data.fetcher import fetch_data
from core.signal.engine import calculate_signals

init(autoreset=True)

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
