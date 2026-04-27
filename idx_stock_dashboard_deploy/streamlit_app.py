import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import yfinance as yf

from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS,
    get_all_idx_tickers
)

st.set_page_config(page_title="IDX Stock Dashboard", layout="wide")

# ─────────────────────────────
# AUTO MARKET REFRESH SYSTEM
# ─────────────────────────────
def get_refresh_interval():
    tz = pytz.timezone("Asia/Jakarta")
    now = datetime.now(tz)

    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    if weekday >= 5:
        return 120

    current_time = hour + minute / 60

    if 9 <= current_time < 12:
        return 15
    if 12 <= current_time < 13.5:
        return 60
    if 13.5 <= current_time < 15:
        return 15

    return 60


# ─────────────────────────────
# SECTOR
# ─────────────────────────────
def get_sector(ticker: str):
    try:
        info = yf.Ticker(add_jk(ticker)).info
        return info.get("sector", "Unknown")
    except:
        return "Unknown"


# ─────────────────────────────
# FORMAT
# ─────────────────────────────
def format_signal(val):
    if val == "BUY":
        return "🟢 BUY"
    elif val == "SELL":
        return "🔴 SELL"
    return "⚪ NEUTRAL"


# ─────────────────────────────
# CHART FUNCTION (FULL ORIGINAL + FIXED)
# ─────────────────────────────
def plot_candlestick_with_signal(df, ticker, signal):
    df = df.copy()

    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA30'] = df['Close'].rolling(30).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float('nan'))
    df['RSI'] = 100 - (100 / (1 + rs))

    buy_dates, buy_prices = [], []
    sell_dates, sell_prices = [], []

    for i in range(1, len(df)):
        ma10_now = df['MA10'].iloc[i]
        ma10_prev = df['MA10'].iloc[i-1]
        ma30_now = df['MA30'].iloc[i]
        ma30_prev = df['MA30'].iloc[i-1]
        rsi_now = df['RSI'].iloc[i]

        if any(pd.isna([ma10_now, ma10_prev, ma30_now, ma30_prev])):
            continue

        if ma10_now > ma30_now and ma10_prev <= ma30_prev and rsi_now < 60:
            buy_dates.append(df.index[i])
            buy_prices.append(df['Low'].iloc[i] * 0.985)

        elif ma10_now < ma30_now and ma10_prev >= ma30_prev and rsi_now > 40:
            sell_dates.append(df.index[i])
            sell_prices.append(df['High'].iloc[i] * 1.015)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price'
    ))

    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA10'], name='MA10'
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA30'], name='MA30'
    ))

    if buy_dates:
        fig.add_trace(go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode='markers',
            name='BUY',
            marker=dict(symbol='triangle-up', size=10, color='green')
        ))

    if sell_dates:
        fig.add_trace(go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode='markers',
            name='SELL',
            marker=dict(symbol='triangle-down', size=10, color='red')
        ))

    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        title=f"{ticker} | {signal}"
    )

    return fig


# ─────────────────────────────
# SIDEBAR
# ─────────────────────────────
st.sidebar.title("⚙️ Settings")

mode = st.sidebar.radio("", ["Auto IDX Full"])

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
    "Tickers",
    ",".join(tickers_source[:30])
)

period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk"], index=0)

run_button = st.sidebar.button("🚀 Scan")
auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh")

# ─────────────────────────────
# AUTO REFRESH FIXED
# ─────────────────────────────
refresh_interval = get_refresh_interval()

if auto_refresh:
    st.sidebar.info(f"⏱️ Refresh: {refresh_interval}s")

    if refresh_interval == 15:
        st.sidebar.success("🟢 Market Active")
    elif refresh_interval == 60:
        st.sidebar.warning("🟡 Market Pause")
    else:
        st.sidebar.info("🔵 Weekend Mode")

    st_autorefresh(
        interval=refresh_interval * 1000,
        key="auto_refresh"
    )


# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 IDX Stock Dashboard Pro")


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
                "Ticker": ticker,
                "Price": sig["price"],
                "RSI": sig["rsi"],
                "Signal": signal,
                "Confidence": sig["confidence"]
            })

        progress.progress((i+1)/len(tickers))

    df_result = pd.DataFrame(results)

    if df_result.empty:
        st.error("No data")
        st.stop()

    # ─────────────────────────────
    # SUMMARY
    # ─────────────────────────────
    st.subheader("📊 Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("BUY", (df_result["Signal"] == "BUY").sum())
    col2.metric("SELL", (df_result["Signal"] == "SELL").sum())
    col3.metric("HOLD", (df_result["Signal"] == "NEUTRAL").sum())

    # ─────────────────────────────
    # TABLE
    # ─────────────────────────────
    st.subheader("📈 Signals")

    df_show = df_result.copy()
    df_show["Signal"] = df_show["Signal"].apply(format_signal)

    st.dataframe(df_show.sort_values("Confidence", ascending=False),
                 use_container_width=True)

    # ─────────────────────────────
    # CHART SECTION (FULL FIXED)
    # ─────────────────────────────
    st.subheader("📉 Chart")

    selected = st.selectbox("Select Stock", df_result["Ticker"])

    df_chart = fetch_data(add_jk(selected), period=period, interval=interval)

    if df_chart is not None:
        signal = df_result[df_result["Ticker"] == selected]["Signal"].values[0]
        fig = plot_candlestick_with_signal(df_chart, selected, signal)
        st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Last update: {datetime.now()}")

else:
    st.info("Click Scan or enable Auto Refresh")
