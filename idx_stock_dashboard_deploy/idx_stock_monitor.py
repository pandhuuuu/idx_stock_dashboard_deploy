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
    print("    pip install yfinance pandas ta-lib colorama tabulate rich\n")
    sys.exit(1)

init(autoreset=True)

# ──────────────────────────────────────────────
# DEFAULT SAHAM IDX (bisa diubah)
# ──────────────────────────────────────────────
DEFAULT_TICKERS = [
    "BBCA", "BBRI", "TLKM", "ASII", "BMRI",
    "UNVR", "GOTO", "ICBP", "KLBF", "ANTM",
    "INDF", "EXCL", "PGAS", "ADRO", "PTBA",
    "AALI", "ABBA", "ABDA", "ABMM", "ACES", 
    "ACST", "ADES", "ADHI", "AISA", "AKKU", 
    "AKPI", "AKRA", "AKSI", "ALDO", "ALKA", 
    "ALMI", "ALTO", "AMAG", "AMFG", "AMIN", 
]

# ──────────────────────────────────────────────
# PARAMETER SINYAL (Berdasarkan Best Practices dari Textbook)
# ──────────────────────────────────────────────
RSI_OVERSOLD      = 30
RSI_OVERBOUGHT    = 70
RSI_NEUTRAL       = 50

VOLUME_SPIKE_X    = 2.0   # volume > X kali rata-rata 20 hari
VOLUME_AVG_PERIOD = 20

MA_SHORT          = 10
MA_LONG           = 30

BREAKOUT_LOOKBACK = 20    # hari untuk hitung high/low

# Bollinger Bands
BB_PERIOD         = 20
BB_STD_DEV        = 2.0

# ATR & Volatility
ATR_PERIOD        = 14
ATR_MULTIPLIER_SL = 2.0    # Stop Loss = Price - (2 * ATR)
ATR_MULTIPLIER_TP = 3.0    # Take Profit = Price + (3 * ATR)

# Stochastic Oscillator
STOCH_PERIOD      = 14
STOCH_SMOOTH      = 3

# Risk-Free Rate untuk Sharpe Ratio (IDR: BI Rate ~6%)
RISK_FREE_RATE    = 0.06


def add_jk(ticker: str) -> str:
    """Tambahkan suffix .JK jika belum ada."""
    return ticker.upper() + ".JK" if not ticker.endswith(".JK") else ticker.upper()


def fetch_data(ticker_jk: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame | None:
    """Ambil data OHLCV dari Yahoo Finance."""
    try:
        df = yf.download(ticker_jk, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < BREAKOUT_LOOKBACK + 5:
            return None
        # Flatten MultiIndex columns jika ada
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"  {Fore.RED}[ERROR] {ticker_jk}: {e}{Style.RESET_ALL}")
        return None


def calculate_signals(df: pd.DataFrame) -> dict:
    """Hitung semua indikator teknikal dan return dict sinyal dengan scoring."""
    close = df["Close"].values
    volume = df["Volume"].values
    high = df["High"].values
    low = df["Low"].values
    
    # ─────────────────────────────────────────────────
    # 1. MOVING AVERAGES (SMA)
    # ─────────────────────────────────────────────────
    sma_s = pd.Series(close).rolling(MA_SHORT).mean().iloc[-1]
    sma_l = pd.Series(close).rolling(MA_LONG).mean().iloc[-1]
    
    ma_cross_up = (close[-1] > sma_s and close[-2] <= pd.Series(close).rolling(MA_SHORT).mean().iloc[-2] and
                   sma_s > sma_l)
    ma_cross_dn = (close[-1] < sma_s and close[-2] >= pd.Series(close).rolling(MA_SHORT).mean().iloc[-2] and
                   sma_s < sma_l)
    ma_trending_up = sma_s > sma_l
    ma_trending_dn = sma_s < sma_l

    # ─────────────────────────────────────────────────
    # 2. RSI (Relative Strength Index) - Wilder's Smoothing
    # ─────────────────────────────────────────────────
    rsi = talib.RSI(close, timeperiod=14)
    rsi_val = float(rsi[-1]) if not pd.isna(rsi[-1]) else 50
    rsi_oversold = rsi_val < RSI_OVERSOLD
    rsi_overbought = rsi_val > RSI_OVERBOUGHT
    rsi_trending_up = rsi_val > RSI_NEUTRAL
    rsi_trending_dn = rsi_val < RSI_NEUTRAL

    # ─────────────────────────────────────────────────
    # 3. MACD (Moving Average Convergence Divergence)
    # ─────────────────────────────────────────────────
    macd_line, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_cross_up = len(macd_hist) > 1 and macd_hist[-1] > 0 and macd_hist[-2] <= 0
    macd_cross_dn = len(macd_hist) > 1 and macd_hist[-1] < 0 and macd_hist[-2] >= 0
    macd_bullish = macd_line[-1] > macd_signal[-1] if len(macd_line) > 0 else False
    macd_bearish = macd_line[-1] < macd_signal[-1] if len(macd_line) > 0 else False

    # ─────────────────────────────────────────────────
    # 4. STOCHASTIC OSCILLATOR
    # ─────────────────────────────────────────────────
    k_percent, d_percent = talib.STOCH(high, low, close, fastk_period=STOCH_PERIOD, 
                                        slowk_period=STOCH_SMOOTH, slowd_period=STOCH_SMOOTH)
    stoch_k = float(k_percent[-1]) if len(k_percent) > 0 and not pd.isna(k_percent[-1]) else 50
    stoch_d = float(d_percent[-1]) if len(d_percent) > 0 and not pd.isna(d_percent[-1]) else 50
    stoch_oversold = stoch_k < 20
    stoch_overbought = stoch_k > 80
    stoch_cross_up = len(k_percent) > 1 and k_percent[-1] > d_percent[-1] and k_percent[-2] <= d_percent[-2]
    stoch_cross_dn = len(k_percent) > 1 and k_percent[-1] < d_percent[-1] and k_percent[-2] >= d_percent[-2]

    # ─────────────────────────────────────────────────
    # 5. BOLLINGER BANDS (untuk volatilitas & signal)
    # ─────────────────────────────────────────────────
    bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=BB_PERIOD, 
                                                  nbdevup=BB_STD_DEV, nbdevdn=BB_STD_DEV)
    price_now = float(close[-1])
    bb_upper_val = float(bb_upper[-1]) if not pd.isna(bb_upper[-1]) else price_now
    bb_lower_val = float(bb_lower[-1]) if not pd.isna(bb_lower[-1]) else price_now
    bb_middle_val = float(bb_middle[-1]) if not pd.isna(bb_middle[-1]) else price_now
    
    bb_width = bb_upper_val - bb_lower_val
    bb_pct_b = ((price_now - bb_lower_val) / bb_width * 100) if bb_width > 0 else 50
    
    bb_overbought = price_now > bb_upper_val  # >100% di %B
    bb_oversold = price_now < bb_lower_val     # <0% di %B
    bb_squeeze = bb_width < (bb_middle_val * 0.1)  # < 10% dari middle band

    # ─────────────────────────────────────────────────
    # 6. ATR (Average True Range) - Volatility & Risk Management
    # ─────────────────────────────────────────────────
    atr = talib.ATR(high, low, close, timeperiod=ATR_PERIOD)
    atr_val = float(atr[-1]) if not pd.isna(atr[-1]) else 0
    
    # Suggested Stop Loss & Take Profit
    suggested_sl = price_now - (ATR_MULTIPLIER_SL * atr_val)
    suggested_tp = price_now + (ATR_MULTIPLIER_TP * atr_val)
    risk_reward = abs(suggested_tp - price_now) / abs(price_now - suggested_sl) if suggested_sl != price_now else 0
    
    # ATR Volatility Level
    atr_pct = (atr_val / price_now * 100) if price_now > 0 else 0

    # ─────────────────────────────────────────────────
    # 7. VOLUME SPIKE (dengan Relative Volume)
    # ─────────────────────────────────────────────────
    vol_avg = pd.Series(volume).rolling(VOLUME_AVG_PERIOD).mean().iloc[-1]
    vol_now = float(volume[-1])
    rvol = vol_now / vol_avg if vol_avg > 0 else 0
    vol_spike = rvol >= VOLUME_SPIKE_X
    
    # ─────────────────────────────────────────────────
    # 8. BREAKOUT / BREAKDOWN (20-day High/Low)
    # ─────────────────────────────────────────────────
    recent_high = high[-(BREAKOUT_LOOKBACK + 1):-1].max()
    recent_low = low[-(BREAKOUT_LOOKBACK + 1):-1].min()
    breakout_up = price_now > recent_high
    breakout_dn = price_now < recent_low

    # ─────────────────────────────────────────────────
    # 9. SIGNAL STRENGTH SCORING (Multi-Factor Analysis)
    # ─────────────────────────────────────────────────
    bull_score = 0
    bear_score = 0
    signals_detail = []
    
    # MA Signals (weight: 2.0)
    if ma_cross_up:
        bull_score += 2.0
        signals_detail.append(f"▲ MA{MA_SHORT}/MA{MA_LONG} Cross UP")
    elif ma_trending_up:
        bull_score += 1.0
    
    if ma_cross_dn:
        bear_score += 2.0
        signals_detail.append(f"▼ MA{MA_SHORT}/MA{MA_LONG} Cross DN")
    elif ma_trending_dn:
        bear_score += 1.0
    
    # RSI Signals (weight: 1.5)
    if rsi_oversold:
        bull_score += 1.5
        signals_detail.append(f"▲ RSI Oversold ({rsi_val:.1f})")
    elif rsi_trending_up:
        bull_score += 0.5
    
    if rsi_overbought:
        bear_score += 1.5
        signals_detail.append(f"▼ RSI Overbought ({rsi_val:.1f})")
    elif rsi_trending_dn:
        bear_score += 0.5
    
    # MACD Signals (weight: 2.0)
    if macd_cross_up:
        bull_score += 2.0
        signals_detail.append("▲ MACD Cross UP")
    elif macd_bullish:
        bull_score += 1.0
    
    if macd_cross_dn:
        bear_score += 2.0
        signals_detail.append("▼ MACD Cross DN")
    elif macd_bearish:
        bear_score += 1.0
    
    # Stochastic Signals (weight: 1.0)
    if stoch_cross_up and stoch_oversold:
        bull_score += 1.5
        signals_detail.append(f"▲ Stoch Cross UP ({stoch_k:.1f})")
    elif stoch_oversold:
        bull_score += 0.8
    
    if stoch_cross_dn and stoch_overbought:
        bear_score += 1.5
        signals_detail.append(f"▼ Stoch Cross DN ({stoch_k:.1f})")
    elif stoch_overbought:
        bear_score += 0.8
    
    # Bollinger Bands Signals (weight: 1.5)
    if bb_oversold and not bb_squeeze:
        bull_score += 1.5
        signals_detail.append(f"▲ BB Oversold ({bb_pct_b:.0f}%)")
    elif bb_squeeze and bull_score > bear_score:
        bull_score += 0.5
        signals_detail.append("⚡ BB Squeeze (Breakout pending)")
    
    if bb_overbought and not bb_squeeze:
        bear_score += 1.5
        signals_detail.append(f"▼ BB Overbought ({bb_pct_b:.0f}%)")
    
    # Volume Signals (weight: 1.0)
    if vol_spike:
        if bull_score >= bear_score:
            bull_score += 1.0
            signals_detail.append(f"▲ Volume Spike ({rvol:.1f}x)")
        else:
            bear_score += 1.0
            signals_detail.append(f"▼ Volume Spike ({rvol:.1f}x)")
    
    # Breakout Signals (weight: 1.5)
    if breakout_up and not breakout_dn:
        bull_score += 1.5
        signals_detail.append(f"▲ Breakout {BREAKOUT_LOOKBACK}d High")
    
    if breakout_dn and not breakout_up:
        bear_score += 1.5
        signals_detail.append(f"▼ Breakdown {BREAKOUT_LOOKBACK}d Low")
    
    # Normalize scores (0-100)
    max_score = max(bull_score, bear_score) if max(bull_score, bear_score) > 0 else 1
    bull_pct = (bull_score / max_score * 100) if max_score > 0 else 0
    bear_pct = (bear_score / max_score * 100) if max_score > 0 else 0
    
    return {
        "price":            round(price_now, 0),
        "rsi":              round(rsi_val, 1),
        "stoch_k":          round(stoch_k, 1),
        "macd_hist":        round(macd_hist[-1], 2) if len(macd_hist) > 0 else 0,
        "bb_pct":           round(bb_pct_b, 0),
        "atr":              round(atr_val, 2),
        "atr_pct":          round(atr_pct, 2),
        "rvol":             round(rvol, 2),
        "vol_ratio":        round(rvol, 1),
        "sma_s":            round(sma_s, 0),
        "sma_l":            round(sma_l, 0),
        "suggested_sl":     round(suggested_sl, 0),
        "suggested_tp":     round(suggested_tp, 0),
        "risk_reward":      round(risk_reward, 2),
        "bull_score":       round(bull_score, 1),
        "bear_score":       round(bear_score, 1),
        "bull_pct":         round(bull_pct, 0),
        "bear_pct":         round(bear_pct, 0),
        "signals":          signals_detail,
        "confidence":       round(max(bull_score, bear_score), 1),  # Signal strength 0-10
    }


def format_row(ticker: str, sig: dict) -> list:
    """Format satu baris output untuk Rich table."""
    ticker_disp = ticker.replace(".JK", "")
    
    bull_score = sig["bull_score"]
    bear_score = sig["bear_score"]
    confidence = sig["confidence"]
    
    # Determine signal direction berdasarkan scoring
    if bull_score > bear_score + 1.0:  # Bullish threshold
        direction = "▲ BUY"
        signal_type = "STRONG BUY" if bull_score >= 5 else "BUY"
    elif bear_score > bull_score + 1.0:  # Bearish threshold
        direction = "▼ SELL"
        signal_type = "STRONG SELL" if bear_score >= 5 else "SELL"
    else:  # Neutral
        direction = "● NEUTRAL"
        signal_type = "NEUTRAL"
    
    # Format RSI dengan plain text (Rich akan handle coloring)
    rsi_val = sig["rsi"]
    rsi_str = f"{rsi_val}"
    
    # Format Stochastic
    stoch_val = sig["stoch_k"]
    stoch_str = f"{stoch_val}"
    
    # Format Volume
    vol_str = f"{sig['vol_ratio']}x"
    
    # Format confidence bar
    confidence_bar = "█" * int(confidence) + "░" * (10 - int(confidence))
    confidence_display = f"[{confidence_bar}]"
    
    # Combine all signals
    signals_text = " | ".join(sig["signals"][:3]) if sig["signals"] else "No signals"
    
    return [
        ticker_disp,
        f"{sig['price']:,.0f}",
        rsi_str,
        stoch_str,
        vol_str,
        f"{sig['atr_pct']:.1f}%",
        direction,
        confidence_display,
        signals_text[:50]
    ]


def run_scan(tickers: list[str], period: str, interval: str):
    console = Console()
    
    # ─────────────────────────────────────────────────
    # HEADER DASHBOARD
    # ─────────────────────────────────────────────────
    header_text = Text("📊 IDX STOCK ENTRY SIGNAL MONITOR", style="bold cyan")
    header_text.append("\nAdvanced Multi-Factor Technical Analysis", style="dim cyan")
    header_panel = Panel(
        Align.center(header_text),
        title="[bold blue]Dashboard[/bold blue]",
        border_style="blue"
    )
    
    # Timestamp & Parameters
    info_text = f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 📈 Period: {period} | 📊 Interval: {interval}"
    info_panel = Panel(info_text, border_style="dim blue")
    
    console.print(header_panel)
    console.print(info_panel)
    console.print()

    # ─────────────────────────────────────────────────
    # PROGRESS BAR SELAMA SCANNING
    # ─────────────────────────────────────────────────
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=True
    ) as progress:
        scan_task = progress.add_task("🔍 Scanning stocks...", total=len(tickers))
        
        rows = []
        for raw in tickers:
            tkr = add_jk(raw)
            df = fetch_data(tkr, period=period, interval=interval)
            if df is None:
                rows.append([raw, "-", "-", "-", "-", "-", "NO DATA", "-", "Data tidak tersedia"])
            else:
                sig = calculate_signals(df)
                rows.append(format_row(tkr, sig))
            progress.update(scan_task, advance=1)
            time.sleep(0.2)  # jangan terlalu agresif hit API

    # ─────────────────────────────────────────────────
    # MAIN DATA TABLE
    # ─────────────────────────────────────────────────
    table = Table(title="📈 Technical Analysis Results", show_header=True, header_style="bold magenta")
    
    table.add_column("Saham", style="cyan", no_wrap=True)
    table.add_column("Harga (Rp)", style="green", justify="right")
    table.add_column("RSI(14)", style="yellow", justify="center")
    table.add_column("Stoch(K)", style="magenta", justify="center")
    table.add_column("Volume", style="blue", justify="center")
    table.add_column("ATR %", style="red", justify="center")
    table.add_column("Signal", style="bold", justify="center")
    table.add_column("Confidence", justify="center")
    table.add_column("Details", style="dim", max_width=50)

    for row in rows:
        # Conditional styling berdasarkan indikator values
        rsi_val = float(row[2]) if row[2] != "-" else 50
        stoch_val = float(row[3]) if row[3] != "-" else 50
        
        # RSI styling
        if rsi_val < RSI_OVERSOLD:
            rsi_style = "green"
        elif rsi_val > RSI_OVERBOUGHT:
            rsi_style = "red"
        elif rsi_val > RSI_NEUTRAL:
            rsi_style = "bright_green"
        elif rsi_val < RSI_NEUTRAL:
            rsi_style = "bright_red"
        else:
            rsi_style = "white"
        
        # Stochastic styling
        if stoch_val < 20:
            stoch_style = "green"
        elif stoch_val > 80:
            stoch_style = "red"
        else:
            stoch_style = "white"
        
        # Volume styling
        vol_style = "cyan" if "x" in row[4] and float(row[4].replace("x", "")) >= VOLUME_SPIKE_X else "white"
        
        # ATR styling (higher volatility = more red)
        atr_val = float(row[5].replace("%", "")) if "%" in row[5] else 0
        atr_style = "red" if atr_val > 5 else "yellow" if atr_val > 3 else "green"
        
        table.add_row(
            f"[cyan]{row[0]}[/cyan]",  # Ticker
            f"[green]{row[1]}[/green]",  # Price
            f"[{rsi_style}]{row[2]}[/{rsi_style}]",  # RSI
            f"[{stoch_style}]{row[3]}[/{stoch_style}]",  # Stochastic
            f"[{vol_style}]{row[4]}[/{vol_style}]",  # Volume
            f"[{atr_style}]{row[5]}[/{atr_style}]",  # ATR
            row[6],  # Signal (already colored)
            f"[blue]{row[7]}[/blue]",  # Confidence
            f"[dim]{row[8]}[/dim]"  # Details
        )

    console.print(table)
    console.print()

    # ─────────────────────────────────────────────────
    # SUMMARY DASHBOARD
    # ─────────────────────────────────────────────────
    buy_list = [r[0] for r in rows if "BUY" in r[6] or "▲" in r[6]]
    sell_list = [r[0] for r in rows if "SELL" in r[6] or "▼" in r[6]]
    neutral_list = [r[0] for r in rows if "NEUTRAL" in r[6] or "●" in r[6]]
    
    # Calculate statistics
    total_stocks = len(rows)
    buy_pct = len(buy_list) / total_stocks * 100 if total_stocks > 0 else 0
    sell_pct = len(sell_list) / total_stocks * 100 if total_stocks > 0 else 0
    neutral_pct = len(neutral_list) / total_stocks * 100 if total_stocks > 0 else 0
    
    # Market Sentiment
    if buy_pct > sell_pct + 10:
        sentiment = "🐂 BULLISH"
        sentiment_color = "green"
    elif sell_pct > buy_pct + 10:
        sentiment = "🐻 BEARISH"
        sentiment_color = "red"
    else:
        sentiment = "⚖️  NEUTRAL"
        sentiment_color = "yellow"

    # Create summary panels
    summary_layout = Layout()
    summary_layout.split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    # Left panel: Signal Summary
    signal_summary = f"""
[bold green]▲ BUY Signals:[/bold green] {len(buy_list)} ({buy_pct:.1f}%)
[green]{', '.join(buy_list[:8])}{'...' if len(buy_list) > 8 else ''}[/green]

[bold red]▼ SELL Signals:[/bold red] {len(sell_list)} ({sell_pct:.1f}%)
[red]{', '.join(sell_list[:8])}{'...' if len(sell_list) > 8 else ''}[/red]

[bold yellow]● NEUTRAL:[/bold yellow] {len(neutral_list)} ({neutral_pct:.1f}%)
[yellow]{', '.join(neutral_list[:8])}{'...' if len(neutral_list) > 8 else ''}[/yellow]
"""
    
    # Right panel: Market Sentiment & Indicators
    sentiment_panel = f"""
[bold {sentiment_color}]{sentiment}[/bold {sentiment_color}]

[bold cyan]📊 Indicators Used:[/bold cyan]
• MA Crossover (10/30 SMA)
• RSI (14) - Oversold: <30, Overbought: >70
• Stochastic (14,3) - Momentum
• MACD (12,26,9) - Trend
• Bollinger Bands (20,2σ) - Volatility
• ATR (14) - Risk Management
• Volume Analysis - Accumulation

[bold magenta]⚠️ Disclaimer:[/bold magenta]
For educational purposes only.
Not investment advice.
"""
    
    summary_layout["left"].update(Panel(signal_summary, title="📋 Signal Summary", border_style="green"))
    summary_layout["right"].update(Panel(sentiment_panel, title="🎯 Market Overview", border_style="blue"))
    
    console.print(summary_layout)
    
    # ─────────────────────────────────────────────────
    # TOP SIGNALS HIGHLIGHT
    # ─────────────────────────────────────────────────
    if buy_list:
        top_buy_text = f"[bold green]🚀 Top Entry Candidates:[/bold green]\n"
        # Sort by confidence (assuming higher confidence = stronger signal)
        top_buy_text += "\n".join(f"• {ticker}" for ticker in buy_list[:3])
        console.print(Panel(top_buy_text, border_style="green"))
    
    if sell_list:
        top_sell_text = f"[bold red]⚠️  Exit/Avoid Signals:[/bold red]\n"
        top_sell_text += "\n".join(f"• {ticker}" for ticker in sell_list[:3])
        console.print(Panel(top_sell_text, border_style="red"))
    
    console.print(f"\n[dim cyan]Dashboard generated at {datetime.now().strftime('%H:%M:%S')} - Total stocks analyzed: {total_stocks}[/dim cyan]\n")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="IDX Stock Entry Signal Monitor")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS,
                        help="Daftar kode saham IDX (tanpa .JK), mis: BBCA TLKM ASII")
    parser.add_argument("--period",   default="3mo",
                        help="Periode data: 1mo 3mo 6mo 1y (default: 3mo)")
    parser.add_argument("--interval", default="1d",
                        help="Interval candle: 1d 1wk (default: 1d)")
    parser.add_argument("--loop", type=int, default=0,
                        help="Ulangi scan setiap N menit (0 = sekali saja)")
    args = parser.parse_args()

    if args.loop > 0:
        print(f"Mode loop aktif: scan setiap {args.loop} menit. Tekan Ctrl+C untuk berhenti.")
        while True:
            run_scan(args.tickers, args.period, args.interval)
            print(f"Scan berikutnya dalam {args.loop} menit...\n")
            time.sleep(args.loop * 60)
    else:
        run_scan(args.tickers, args.period, args.interval)


if __name__ == "__main__":
    main()
