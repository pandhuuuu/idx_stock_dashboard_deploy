import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS
)

st.set_page_config(layout="wide", page_title="Trading Dashboard PRO")

# ─────────────────────────────
# AUTO REFRESH
# ─────────────────────────────
if st.sidebar.checkbox("🔄 Auto Refresh"):
    st_autorefresh(interval=60000, key="refresh")

# ─────────────────────────────
# SIDEBAR
# ─────────────────────────────
st.sidebar.title("⚙️ Control Panel")

tickers_input = st.sidebar.text_area(
    "Kode Saham",
    ",".join(DEFAULT_TICKERS[:8])
)

period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y"])
interval = st.sidebar.selectbox("Interval", ["1d", "1wk"])

filter_signal = st.sidebar.selectbox(
    "Filter Signal",
    ["ALL", "BUY", "SELL", "NEUTRAL"]
)

# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 Trading Dashboard PRO")
st.caption("Mini TradingView Style Dashboard")

tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

results = []

# ─────────────────────────────
# SCAN
# ─────────────────────────────
for ticker in tickers:
    df = fetch_data(add_jk(ticker), period, interval)

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
            "Harga": sig["price"],
            "RSI": sig["rsi"],
            "Signal": signal,
            "Confidence": sig["confidence"]
        })

df_result = pd.DataFrame(results)

# FILTER
if filter_signal != "ALL":
    df_result = df_result[df_result["Signal"] == filter_signal]

# ─────────────────────────────
# TABLE
# ─────────────────────────────
st.subheader("📈 Market Scanner")

st.dataframe(
    df_result.sort_values(by="Confidence", ascending=False),
    use_container_width=True
)

# ─────────────────────────────
# SELECT STOCK
# ─────────────────────────────
st.subheader("📉 Chart Analysis")

selected = st.selectbox("Pilih Saham", df_result["Saham"])

df_chart = fetch_data(add_jk(selected), period, interval)

# ─────────────────────────────
# INDICATORS
# ─────────────────────────────
df_chart["MA10"] = df_chart["Close"].rolling(10).mean()
df_chart["MA30"] = df_chart["Close"].rolling(30).mean()

# RSI
delta = df_chart["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
df_chart["RSI"] = 100 - (100 / (1 + rs))

# MACD
exp1 = df_chart["Close"].ewm(span=12).mean()
exp2 = df_chart["Close"].ewm(span=26).mean()
df_chart["MACD"] = exp1 - exp2
df_chart["SignalLine"] = df_chart["MACD"].ewm(span=9).mean()

# ─────────────────────────────
# LAYOUT GRID
# ─────────────────────────────
col1, col2 = st.columns([3,1])

# ───────── LEFT (CHART)
with col1:

    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df_chart.index,
        open=df_chart['Open'],
        high=df_chart['High'],
        low=df_chart['Low'],
        close=df_chart['Close'],
        name='Price'
    ))

    # MA
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA10'], name="MA10"))
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA30'], name="MA30"))

    fig.update_layout(height=500)

    st.plotly_chart(fig, use_container_width=True)

# ───────── RIGHT (INFO PANEL)
with col2:

    row = df_result[df_result["Saham"] == selected].iloc[0]

    st.metric("Harga", row["Harga"])
    st.metric("RSI", row["RSI"])
    st.metric("Signal", row["Signal"])
    st.metric("Confidence", row["Confidence"])

# ─────────────────────────────
# RSI CHART
# ─────────────────────────────
st.subheader("📊 RSI")

fig_rsi = go.Figure()
fig_rsi.add_trace(go.Scatter(x=df_chart.index, y=df_chart["RSI"], name="RSI"))
fig_rsi.add_hline(y=70)
fig_rsi.add_hline(y=30)

st.plotly_chart(fig_rsi, use_container_width=True)

# ─────────────────────────────
# MACD CHART
# ─────────────────────────────
st.subheader("📊 MACD")

fig_macd = go.Figure()
fig_macd.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MACD"], name="MACD"))
fig_macd.add_trace(go.Scatter(x=df_chart.index, y=df_chart["SignalLine"], name="Signal"))

st.plotly_chart(fig_macd, use_container_width=True)

# ─────────────────────────────
# FOOTER
# ─────────────────────────────
st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.warning("⚠️ Educational only - Not financial advice")
