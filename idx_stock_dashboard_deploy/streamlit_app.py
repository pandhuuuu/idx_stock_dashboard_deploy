"""
GANTI seluruh fungsi plot_candlestick_with_signal di app Streamlit kamu
dengan kode di bawah ini.

Fitur baru:
  - Historical Buy-point & Sell-point (semua candle, bukan hanya terakhir)
  - Label badge hijau/merah mirip TradingView
  - Support & Resistance horizontal lines (otomatis dari swing high/low)
  - Trendline (regresi linier dari swing-low)
  - Volume bar di panel bawah
  - Tampilan candlestick lebih rapi
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats  # pip install scipy


# ─────────────────────────────────────────────────────────────
# HELPER: Deteksi swing high / swing low
# ─────────────────────────────────────────────────────────────
def _swing_points(series: pd.Series, window: int = 5):
    """Return index positions of local maxima and minima."""
    highs, lows = [], []
    for i in range(window, len(series) - window):
        window_slice = series.iloc[i - window: i + window + 1]
        if series.iloc[i] == window_slice.max():
            highs.append(i)
        if series.iloc[i] == window_slice.min():
            lows.append(i)
    return highs, lows


# ─────────────────────────────────────────────────────────────
# HELPER: Generate buy/sell signals dari RSI + MA crossover
# ─────────────────────────────────────────────────────────────
def _generate_historical_signals(df: pd.DataFrame):
    """
    Hitung RSI dan MA crossover untuk seluruh candle, lalu
    kembalikan daftar index buy & sell.

    Buy  : RSI < 35 DAN MA10 baru saja memotong MA30 ke atas
    Sell : RSI > 65 DAN MA10 baru saja memotong MA30 ke bawah
    """
    close = df["Close"]

    # RSI-14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # Moving averages
    ma10 = close.rolling(10).mean()
    ma30 = close.rolling(30).mean()

    buy_idx, sell_idx = [], []
    for i in range(1, len(df)):
        # MA crossover: golden cross → buy, death cross → sell
        golden = (ma10.iloc[i] > ma30.iloc[i]) and (ma10.iloc[i - 1] <= ma30.iloc[i - 1])
        death  = (ma10.iloc[i] < ma30.iloc[i]) and (ma10.iloc[i - 1] >= ma30.iloc[i - 1])

        if golden and rsi.iloc[i] < 55:
            buy_idx.append(i)
        elif death and rsi.iloc[i] > 45:
            sell_idx.append(i)

    return buy_idx, sell_idx


# ─────────────────────────────────────────────────────────────
# HELPER: Support & Resistance dari swing points
# ─────────────────────────────────────────────────────────────
def _support_resistance(df: pd.DataFrame, n_levels: int = 3):
    """Return up to n support prices dan n resistance prices."""
    _, lows_idx  = _swing_points(df["Low"],  window=5)
    highs_idx, _ = _swing_points(df["High"], window=5)

    # Ambil n terakhir
    supports    = sorted([df["Low"].iloc[i]  for i in lows_idx[-n_levels:]])
    resistances = sorted([df["High"].iloc[i] for i in highs_idx[-n_levels:]], reverse=True)
    return supports, resistances


# ─────────────────────────────────────────────────────────────
# HELPER: Trendline dari swing lows (regresi linier)
# ─────────────────────────────────────────────────────────────
def _trendline(df: pd.DataFrame):
    """Fit linear regression through swing lows. Return (y_start, y_end)."""
    _, lows_idx = _swing_points(df["Low"], window=5)
    if len(lows_idx) < 2:
        return None, None

    x = np.array(lows_idx)
    y = np.array([df["Low"].iloc[i] for i in lows_idx])
    slope, intercept, *_ = stats.linregress(x, y)

    y_start = intercept + slope * 0
    y_end   = intercept + slope * (len(df) - 1)
    return y_start, y_end


# ─────────────────────────────────────────────────────────────
# MAIN: Candlestick chart dengan semua fitur
# ─────────────────────────────────────────────────────────────
def plot_candlestick_with_signal(df: pd.DataFrame, ticker: str, signal: str):
    """
    Parameters
    ----------
    df      : DataFrame dari fetch_data (Open, High, Low, Close, Volume)
    ticker  : Nama saham (untuk judul)
    signal  : "BUY" | "SELL" | "NEUTRAL" (dipakai untuk marker terakhir)

    Returns
    -------
    plotly.graph_objects.Figure
    """

    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title=f"{ticker} — No data", height=550)
        return fig

    # ── Moving averages ──────────────────────────────────────
    df = df.copy()
    df["MA10"] = df["Close"].rolling(10).mean()
    df["MA30"] = df["Close"].rolling(30).mean()

    # ── Signals, S/R, trendline ──────────────────────────────
    buy_idx, sell_idx   = _generate_historical_signals(df)
    supports, resistances = _support_resistance(df)
    tl_start, tl_end    = _trendline(df)

    # ── Layout: 2 rows (candlestick 75% + volume 25%) ────────
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.02,
    )

    # ── Candlestick ──────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        name="Price",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a",
        decreasing_fillcolor="#ef5350",
        line_width=1,
    ), row=1, col=1)

    # ── MA lines ─────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA10"],
        name="MA10", line=dict(color="#2196F3", width=1.5),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA30"],
        name="MA30", line=dict(color="#FF9800", width=1.5),
    ), row=1, col=1)

    # ── Trendline ────────────────────────────────────────────
    if tl_start is not None:
        fig.add_trace(go.Scatter(
            x=[df.index[0], df.index[-1]],
            y=[tl_start, tl_end],
            name="Trendline",
            mode="lines",
            line=dict(color="#FF5252", width=1.5, dash="dot"),
        ), row=1, col=1)

    # ── Support lines ────────────────────────────────────────
    for i, s in enumerate(supports):
        fig.add_hline(
            y=s, line_width=1.2, line_dash="dash",
            line_color="#1565C0",
            annotation_text=f"Support {i+1}  {s:,.0f}",
            annotation_position="left",
            annotation_font=dict(color="#1565C0", size=10),
            row=1, col=1,
        )

    # ── Resistance lines ─────────────────────────────────────
    for i, r in enumerate(resistances):
        fig.add_hline(
            y=r, line_width=1.2, line_dash="dash",
            line_color="#B71C1C",
            annotation_text=f"Resistance {i+1}  {r:,.0f}",
            annotation_position="left",
            annotation_font=dict(color="#B71C1C", size=10),
            row=1, col=1,
        )

    # ── Historical BUY markers ───────────────────────────────
    if buy_idx:
        buy_dates  = [df.index[i] for i in buy_idx]
        buy_prices = [df["Low"].iloc[i] * 0.985 for i in buy_idx]   # sedikit di bawah candle
        buy_labels = [f"Buy-point" for _ in buy_idx]

        fig.add_trace(go.Scatter(
            x=buy_dates, y=buy_prices,
            mode="markers+text",
            name="Buy Signal",
            text=buy_labels,
            textposition="bottom center",
            textfont=dict(size=9, color="white"),
            marker=dict(
                symbol="triangle-up",
                size=14,
                color="#00C853",
                line=dict(color="#007E33", width=1),
            ),
            hovertemplate="<b>Buy-point</b><br>%{x}<br>Price: %{customdata:,.0f}<extra></extra>",
            customdata=[df["Close"].iloc[i] for i in buy_idx],
        ), row=1, col=1)

        # Label badge (annotation) untuk setiap buy point
        for i, (d, p) in enumerate(zip(buy_dates, buy_prices)):
            fig.add_annotation(
                x=d, y=p,
                text="Buy-point",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#00C853",
                arrowsize=0.8,
                ax=0, ay=28,
                bgcolor="#00C853",
                bordercolor="#007E33",
                borderwidth=1,
                borderpad=3,
                font=dict(color="white", size=9, family="Arial"),
                opacity=0.9,
                row=1, col=1,
            )

    # ── Historical SELL markers ──────────────────────────────
    if sell_idx:
        sell_dates  = [df.index[i] for i in sell_idx]
        sell_prices = [df["High"].iloc[i] * 1.015 for i in sell_idx]  # sedikit di atas candle
        sell_labels = [f"Sell-point" for _ in sell_idx]

        fig.add_trace(go.Scatter(
            x=sell_dates, y=sell_prices,
            mode="markers+text",
            name="Sell Signal",
            text=sell_labels,
            textposition="top center",
            textfont=dict(size=9, color="white"),
            marker=dict(
                symbol="triangle-down",
                size=14,
                color="#F44336",
                line=dict(color="#B71C1C", width=1),
            ),
            hovertemplate="<b>Sell-point</b><br>%{x}<br>Price: %{customdata:,.0f}<extra></extra>",
            customdata=[df["Close"].iloc[i] for i in sell_idx],
        ), row=1, col=1)

        # Label badge untuk setiap sell point
        for i, (d, p) in enumerate(zip(sell_dates, sell_prices)):
            fig.add_annotation(
                x=d, y=p,
                text="Sell-point",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#F44336",
                arrowsize=0.8,
                ax=0, ay=-28,
                bgcolor="#F44336",
                bordercolor="#B71C1C",
                borderwidth=1,
                borderpad=3,
                font=dict(color="white", size=9, family="Arial"),
                opacity=0.9,
                row=1, col=1,
            )

    # ── Volume bar ───────────────────────────────────────────
    if "Volume" in df.columns:
        vol_colors = [
            "#26a69a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef5350"
            for i in range(len(df))
        ]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"],
            name="Volume",
            marker_color=vol_colors,
            opacity=0.6,
            showlegend=False,
        ), row=2, col=1)

    # ── Layout theming (mirip TradingView dark) ───────────────
    fig.update_layout(
        title=dict(
            text=f"<b>{ticker}</b>  |  Current Signal: "
                 f"{'🟢 BUY' if signal == 'BUY' else '🔴 SELL' if signal == 'SELL' else '⚪ NEUTRAL'}",
            font=dict(size=15),
        ),
        height=600,
        xaxis_rangeslider_visible=False,
        plot_bgcolor="#131722",
        paper_bgcolor="#131722",
        font=dict(color="#D1D4DC"),
        legend=dict(
            orientation="h", x=0, y=1.02,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10),
        ),
        margin=dict(l=60, r=60, t=60, b=20),
        hovermode="x unified",
    )

    fig.update_xaxes(
        gridcolor="#1e2535",
        showgrid=True,
        zeroline=False,
        showspikes=True,
        spikecolor="#555",
        spikethickness=1,
    )
    fig.update_yaxes(
        gridcolor="#1e2535",
        showgrid=True,
        zeroline=False,
        showspikes=True,
        spikecolor="#555",
        spikethickness=1,
        tickformat=",",
    )

    return fig
