import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import yfinance as yf

# IMPORT LOGIC
from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS,
    get_all_idx_tickers
)

st.set_page_config(page_title="IDX Stock Dashboard", layout="wide")

# ─────────────────────────────
# SECTOR FUNCTION
# ─────────────────────────────
def get_sector(ticker: str):
    try:
        info = yf.Ticker(add_jk(ticker)).info
        return info.get("sector", "Unknown")
    except:
        return "Unknown"


# ─────────────────────────────
# SAFE COLOR FORMAT (NO STYLER ERROR)
# ─────────────────────────────
def format_signal(val):
    if val == "BUY":
        return "🟢 BUY"
    elif val == "SELL":
        return "🔴 SELL"
    else:
        return "⚪ NEUTRAL"


def format_number(val):
    try:
        v = float(val)
        if v > 0:
            return f"🟢 {v}"
        elif v < 0:
            return f"🔴 {v}"
        else:
            return f"⚪ {v}"
    except:
        return val


# ─────────────────────────────
# SIDEBAR
# ─────────────────────────────
st.sidebar.title("⚙️ Settings")

mode = st.sidebar.radio(
    "Mode Data",
    ["Manual Tickers", "Auto IDX Full"]
)

if mode == "Auto IDX Full":
    try:
        tickers_source = get_all_idx_tickers()
        if not tickers_source:
            tickers_source = DEFAULT_TICKERS
    except:
        tickers_source = DEFAULT_TICKERS
else:
    tickers_source = DEFAULT_TICKERS

tickers_input = st.sidebar.text_area(
    "Kode Saham (pisah koma)",
    ",".join(tickers_source[:100])
)

period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk"], index=0)

run_button = st.sidebar.button("🚀 Scan Sekarang")

auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh")
refresh_interval = st.sidebar.slider("Interval (detik)", 10, 300, 60)

if auto_refresh:
    try:
        st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")
    except:
        st.warning("Module autorefresh belum terinstall")

# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 IDX Trading Dashboard PRO")
st.caption("Scanner + Trading Plan + Sector Analyzer + Chart")


# ─────────────────────────────
# CHART  ← HANYA BAGIAN INI YANG DIUBAH
# ─────────────────────────────
def plot_candlestick_with_signal(df, ticker, signal):
    df = df.copy()

    # MA
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA30'] = df['Close'].rolling(30).mean()

    # RSI-14 (tanpa library tambahan)
    delta = df['Close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float('nan'))
    df['RSI'] = 100 - (100 / (1 + rs))

    # Deteksi historical buy/sell dari MA crossover + RSI
    buy_dates, buy_prices   = [], []
    sell_dates, sell_prices = [], []

    for i in range(1, len(df)):
        ma10_now  = df['MA10'].iloc[i]
        ma10_prev = df['MA10'].iloc[i - 1]
        ma30_now  = df['MA30'].iloc[i]
        ma30_prev = df['MA30'].iloc[i - 1]
        rsi_now   = df['RSI'].iloc[i]

        if any(v != v for v in [ma10_now, ma10_prev, ma30_now, ma30_prev]):  # skip NaN
            continue

        # Golden cross → BUY
        if ma10_now > ma30_now and ma10_prev <= ma30_prev and rsi_now < 60:
            buy_dates.append(df.index[i])
            buy_prices.append(df['Low'].iloc[i] * 0.985)

        # Death cross → SELL
        elif ma10_now < ma30_now and ma10_prev >= ma30_prev and rsi_now > 40:
            sell_dates.append(df.index[i])
            sell_prices.append(df['High'].iloc[i] * 1.015)

    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
    ))

    # MA lines
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA10'],
        name='MA10',
        line=dict(color='#2196F3', width=1.5)
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA30'],
        name='MA30',
        line=dict(color='#FF9800', width=1.5)
    ))

    # Historical BUY markers + badge label
    if buy_dates:
        fig.add_trace(go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode='markers',
            name='Buy Signal',
            marker=dict(symbol='triangle-up', size=14,
                        color='#00C853', line=dict(color='#007E33', width=1)),
            hovertemplate='<b>Buy-point</b><br>%{x}<extra></extra>'
        ))
        for d, p in zip(buy_dates, buy_prices):
            fig.add_annotation(
                x=d, y=p,
                text="Buy-point",
                showarrow=True, arrowhead=2,
                arrowcolor='#00C853', ax=0, ay=30,
                bgcolor='#00C853', bordercolor='#007E33',
                borderwidth=1, borderpad=3,
                font=dict(color='white', size=9),
                opacity=0.9
            )

    # Historical SELL markers + badge label
    if sell_dates:
        fig.add_trace(go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode='markers',
            name='Sell Signal',
            marker=dict(symbol='triangle-down', size=14,
                        color='#F44336', line=dict(color='#B71C1C', width=1)),
            hovertemplate='<b>Sell-point</b><br>%{x}<extra></extra>'
        ))
        for d, p in zip(sell_dates, sell_prices):
            fig.add_annotation(
                x=d, y=p,
                text="Sell-point",
                showarrow=True, arrowhead=2,
                arrowcolor='#F44336', ax=0, ay=-30,
                bgcolor='#F44336', bordercolor='#B71C1C',
                borderwidth=1, borderpad=3,
                font=dict(color='white', size=9),
                opacity=0.9
            )

    # Support & Resistance otomatis (5 swing point terakhir)
    window = 5
    highs_idx, lows_idx = [], []
    for i in range(window, len(df) - window):
        slice_h = df['High'].iloc[i - window: i + window + 1]
        slice_l = df['Low'].iloc[i - window: i + window + 1]
        if df['High'].iloc[i] == slice_h.max():
            highs_idx.append(i)
        if df['Low'].iloc[i] == slice_l.min():
            lows_idx.append(i)

    for idx in lows_idx[-3:]:
        s = df['Low'].iloc[idx]
        fig.add_hline(
            y=s, line_width=1, line_dash='dash', line_color='#1565C0',
            annotation_text=f"Support {s:,.0f}",
            annotation_font=dict(color='#1565C0', size=9),
            annotation_position='right'
        )

    for idx in highs_idx[-3:]:
        r = df['High'].iloc[idx]
        fig.add_hline(
            y=r, line_width=1, line_dash='dash', line_color='#B71C1C',
            annotation_text=f"Resistance {r:,.0f}",
            annotation_font=dict(color='#B71C1C', size=9),
            annotation_position='right'
        )

    # Trendline dari swing lows (manual, tanpa scipy)
    if len(lows_idx) >= 2:
        x_pts = lows_idx[-5:]
        y_pts = [df['Low'].iloc[i] for i in x_pts]
        n = len(x_pts)
        x_mean = sum(x_pts) / n
        y_mean = sum(y_pts) / n
        slope = sum((x_pts[i] - x_mean) * (y_pts[i] - y_mean) for i in range(n)) / \
                sum((x_pts[i] - x_mean) ** 2 for i in range(n))
        intercept = y_mean - slope * x_mean

        tl_y_start = intercept + slope * 0
        tl_y_end   = intercept + slope * (len(df) - 1)

        fig.add_trace(go.Scatter(
            x=[df.index[0], df.index[-1]],
            y=[tl_y_start, tl_y_end],
            name='Trendline',
            mode='lines',
            line=dict(color='#FF5252', width=1.5, dash='dot')
        ))

    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        title=f"{ticker}  |  {'🟢 BUY' if signal == 'BUY' else '🔴 SELL' if signal == 'SELL' else '⚪ NEUTRAL'}",
        hovermode='x unified'
    )

    return fig


# ─────────────────────────────
# SECTOR MAP
# ─────────────────────────────
sector_map = {
    "BANK": ["BBCA", "BBRI", "BMRI", "MEGA", "BRIS", "BBNI"],
    "ENERGY": ["ADRO", "PTBA", "PGAS", "MEDC", "ITMG"],
    "MINING": ["ANTM", "MDKA", "INCO", "BRMS", "EMAS", "PSAB"],
    "CONSUMER": ["UNVR", "ICBP", "INDF", "MYOR"],
    "TELECOM": ["TLKM", "EXCL", "ISAT"],
    "TECH": ["GOTO", "WIFI"],
}


# ─────────────────────────────
# MAIN
# ─────────────────────────────
if run_button or auto_refresh:

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    results = []

    progress = st.progress(0)
    status = st.empty()

    for i, ticker in enumerate(tickers):
        status.text(f"Scanning {ticker}...")

        df = fetch_data(add_jk(ticker), period=period, interval=interval)

        if df is not None:
            sig = calculate_signals(df)

            if sig["bull_score"] > sig["bear_score"] + 1:
                signal = "BUY"
            elif sig["bear_score"] > sig["bull_score"] + 1:
                signal = "SELL"
            else:
                signal = "NEUTRAL"

            results.append({
                "Saham": ticker,
                "Sektor": get_sector(ticker),
                "Harga": sig["price"],
                "RSI": sig["rsi"],
                "Signal": signal,
                "Confidence": sig["confidence"],
                "Entry": sig["price"],
                "Take Profit": sig["suggested_tp"],
                "Cut Loss": sig["suggested_sl"],
                "RR Ratio": sig["risk_reward"],
            })

        progress.progress((i + 1) / len(tickers))

    status.text("✅ Scan selesai!")

    df_result = pd.DataFrame(results)

    if df_result.empty:
        st.error("❌ Tidak ada data")
        st.stop()

    df_result["Action"] = df_result["Signal"].apply(
        lambda x: "HOLD" if x == "NEUTRAL" else x
    )

    # ─────────────────────────────
    # SUMMARY
    # ─────────────────────────────
    st.subheader("📊 Market Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("BUY", (df_result["Signal"] == "BUY").sum())
    col2.metric("SELL", (df_result["Signal"] == "SELL").sum())
    col3.metric("HOLD", (df_result["Action"] == "HOLD").sum())

    # ─────────────────────────────
    # SECTOR
    # ─────────────────────────────
    st.subheader("🏭 Sector Breakdown")

    sector_df = df_result.groupby("Sektor").agg(
        Total=("Saham", "count"),
        Buy=("Signal", lambda x: (x == "BUY").sum()),
        Sell=("Signal", lambda x: (x == "SELL").sum()),
        Hold=("Action", lambda x: (x == "HOLD").sum()),
    ).reset_index()

    st.dataframe(sector_df, use_container_width=True)

    # ─────────────────────────────
    # MAIN TABLE (COLORED)
    # ─────────────────────────────
    st.subheader("📈 Market Scanner")

    df_display = df_result.copy()
    df_display["Signal"] = df_display["Signal"].apply(format_signal)

    st.dataframe(df_display.sort_values(by="Confidence", ascending=False),
                 use_container_width=True)

    # ─────────────────────────────
    # TOP SIGNALS
    # ─────────────────────────────
    st.subheader("🎯 Top Trading Signals")

    top_buy = df_result[df_result["Signal"] == "BUY"] \
        .sort_values(by="Confidence", ascending=False).head(5)

    top_sell = df_result[df_result["Signal"] == "SELL"] \
        .sort_values(by="Confidence", ascending=False).head(5)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟢 Top BUY")
        top_buy["Signal"] = top_buy["Signal"].apply(format_signal)
        st.dataframe(top_buy, use_container_width=True)

    with col2:
        st.markdown("### 🔴 Top SELL")
        top_sell["Signal"] = top_sell["Signal"].apply(format_signal)
        st.dataframe(top_sell, use_container_width=True)

    # ─────────────────────────────
    # TRADING PLAN
    # ─────────────────────────────
    st.subheader("💰 Trading Plan")

    plan_df = df_result[[
        "Saham", "Sektor", "Harga",
        "Entry", "Take Profit", "Cut Loss",
        "RR Ratio", "Action", "Confidence"
    ]].sort_values(by="Confidence", ascending=False)

    plan_df["Action"] = plan_df["Action"].apply(format_signal)

    st.dataframe(plan_df, use_container_width=True)

    # ─────────────────────────────
    # SECTOR TABLES
    # ─────────────────────────────
    st.subheader("🏭 Sector Tables")

    for sector, list_stock in sector_map.items():
        sdf = df_result[df_result["Saham"].isin(list_stock)]

        if not sdf.empty:
            st.markdown(f"### {sector}")
            sdf["Signal"] = sdf["Signal"].apply(format_signal)
            st.dataframe(sdf, use_container_width=True)

    # ─────────────────────────────
    # CHART
    # ─────────────────────────────
    st.subheader("📉 Chart")

    selected = st.selectbox("Pilih Saham", df_result["Saham"])

    row = df_result[df_result["Saham"] == selected].iloc[0]
    df_chart = fetch_data(add_jk(selected), period=period, interval=interval)

    if df_chart is not None:
        fig = plot_candlestick_with_signal(df_chart, selected, row["Signal"])
        st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Last update: {datetime.now()}")
    st.warning("⚠️ Not financial advice")

else:
    st.info("Klik Scan atau aktifkan Auto Refresh")
