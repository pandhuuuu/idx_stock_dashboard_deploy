import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import pytz

from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS,
    get_all_idx_tickers
)

st.set_page_config(page_title="IDX Stock Dashboard", layout="wide", page_icon="📊")

# ─────────────────────────────
# MARKET STATUS
# ─────────────────────────────
def is_market_open():
    tz = pytz.timezone("Asia/Jakarta")
    now = datetime.now(tz)

    if now.weekday() >= 5:
        return False

    hour = now.hour
    minute = now.minute
    time_val = hour + minute / 60

    return 9 <= time_val <= 15


# ─────────────────────────────
# CUSTOM CSS
# ─────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }

    [data-testid="metric-container"] {
        background: #1a1d27;
        border: 1px solid #2a2d3e;
        border-radius: 10px;
        padding: 16px;
    }

    h2, h3 {
        border-left: 3px solid #4f8ef7;
        padding-left: 10px;
    }

    [data-testid="stSidebar"] {
        background-color: #13151f;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────
# SESSION STATE
# ─────────────────────────────
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

if "scan_results" not in st.session_state:
    st.session_state.scan_results = None


# ─────────────────────────────
# CACHE DATA
# ─────────────────────────────
@st.cache_data(ttl=300)
def cached_fetch(ticker_jk, period, interval):
    return fetch_data(ticker_jk, period=period, interval=interval)


# ─────────────────────────────
# HELPERS
# ─────────────────────────────
def get_sector(ticker: str):
    try:
        info = yf.Ticker(add_jk(ticker)).info
        return info.get("sector", "Unknown")
    except:
        return "Unknown"


def format_signal(val):
    if val == "BUY":
        return "🟢 BUY"
    elif val == "SELL":
        return "🔴 SELL"
    return "⚪ NEUTRAL"


# ─────────────────────────────
# SIDEBAR
# ─────────────────────────────
st.sidebar.title("⚙️ Settings")

mode = st.sidebar.radio("Mode", ["Manual Tickers", "Auto IDX Full"])

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
    "Kode Saham", ",".join(tickers_source[:10])
)

period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk"], index=0)

run_button = st.sidebar.button("🚀 Scan")
auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh")
refresh_interval = st.sidebar.slider("Interval (detik)", 10, 300, 60)

# ─────────────────────────────
# AUTO REFRESH SMART
# ─────────────────────────────
if auto_refresh:
    if is_market_open():
        st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")
    else:
        st.info("Market tutup - auto refresh OFF")


# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 IDX Trading Dashboard PRO")


# ─────────────────────────────
# CHART
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

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.2, 0.2])

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name="MA10"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA30'], name="MA30"), row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume"), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI"), row=3, col=1)

    fig.update_layout(height=600, title=f"{ticker} | {signal}")

    return fig


# ─────────────────────────────
# MAIN SCAN
# ─────────────────────────────
if run_button or auto_refresh:

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    results = []

    progress = st.progress(0)
    status = st.empty()

    for i, ticker in enumerate(tickers):
        status.text(f"Scanning {ticker}...")

        df = cached_fetch(add_jk(ticker), period, interval)

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
                "TP": sig["suggested_tp"],
                "SL": sig["suggested_sl"],
            })

        progress.progress((i + 1) / len(tickers))

    st.session_state.scan_results = pd.DataFrame(results)
    status.text("Done")


# ─────────────────────────────
# DISPLAY
# ─────────────────────────────
if st.session_state.scan_results is not None:

    df = st.session_state.scan_results

    st.subheader("📊 Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("BUY", (df["Signal"] == "BUY").sum())
    col2.metric("SELL", (df["Signal"] == "SELL").sum())
    col3.metric("HOLD", (df["Signal"] == "NEUTRAL").sum())

    st.subheader("📈 Results")
    df_show = df.copy()
    df_show["Signal"] = df_show["Signal"].apply(format_signal)

    st.dataframe(df_show, use_container_width=True)

    st.subheader("📉 Chart")

    selected = st.selectbox("Pilih Saham", df["Saham"])
    row = df[df["Saham"] == selected].iloc[0]

    df_chart = cached_fetch(add_jk(selected), period, interval)

    if df_chart is not None:
        fig = plot_candlestick_with_signal(df_chart, selected, row["Signal"])
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Klik Scan untuk mulai")
