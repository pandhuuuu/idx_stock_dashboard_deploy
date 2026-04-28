import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS,
    get_all_idx_tickers
)

st.set_page_config(page_title="IDX Stock Dashboard", layout="wide", page_icon="📊")

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
    [data-testid="metric-container"] label { color: #8b8fa8 !important; font-size: 13px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 700;
    }
    h2, h3 { border-left: 3px solid #4f8ef7; padding-left: 10px; }
    [data-testid="stSidebar"] { background-color: #13151f; }
    .stButton > button {
        background: linear-gradient(135deg, #4f8ef7, #3a6fd8);
        color: white;
        border-radius: 8px;
        width: 100%;
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
# CACHED FETCH
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
    else:
        return "⚪ NEUTRAL"


# ─────────────────────────────
# SIDEBAR
# ─────────────────────────────
st.sidebar.title("⚙️ Settings")

mode = st.sidebar.radio("Mode Data", ["Auto IDX Full"])

if mode == "Auto IDX Full":
    try:
        tickers_source = get_all_idx_tickers() or DEFAULT_TICKERS
    except:
        tickers_source = DEFAULT_TICKERS
else:
    tickers_source = DEFAULT_TICKERS

tickers_input = st.sidebar.text_area(
    "Kode Saham (pisah koma)",
    ",".join(tickers_source[:30])
)

period   = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk"], index=0)

run_button   = st.sidebar.button("🚀 Scan Sekarang")
auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh")
refresh_interval = st.sidebar.slider("Interval (detik)", 10, 300, 60)

# FIX: hanya 1 autorefresh
if auto_refresh:
    try:
        st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")
    except:
        st.warning("Module autorefresh belum terinstall")


# ─────────────────────────────
# WATCHLIST
# ─────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### ⭐ Watchlist")

add_watch = st.sidebar.text_input("Tambah ke Watchlist")

if st.sidebar.button("➕ Tambah") and add_watch.strip():
    t = add_watch.strip().upper()
    if t not in st.session_state.watchlist:
        st.session_state.watchlist.append(t)
        st.toast(f"{t} ditambahkan")

# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 IDX Dashboard PRO")


# ─────────────────────────────
# SCAN
# ─────────────────────────────
if run_button or auto_refresh:

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    results = []

    progress = st.progress(0)
    status = st.empty()

    for i, ticker in enumerate(tickers):

        status.text(f"Scanning {ticker}...")

        df = cached_fetch(add_jk(ticker), period, interval)

        # ❗ FIX 1: df safety
        if df is None or df.empty:
            progress.progress((i + 1) / len(tickers))
            continue

        sig = calculate_signals(df)

        # ❗ FIX 2: sig safety (INI YANG ERROR KAMU)
        if sig is None or not isinstance(sig, dict):
            progress.progress((i + 1) / len(tickers))
            continue

        bull = sig.get("bull_score", 0)
        bear = sig.get("bear_score", 0)

        if bull > bear + 1:
            signal = "BUY"
        elif bear > bull + 1:
            signal = "SELL"
        else:
            signal = "NEUTRAL"

        results.append({
            "Saham": ticker,
            "Sektor": get_sector(ticker),
            "Harga": sig.get("price", 0),
            "RSI": sig.get("rsi", 0),
            "Signal": signal,
            "Confidence": sig.get("confidence", 0),
            "Entry": sig.get("price", 0),
            "Take Profit": sig.get("suggested_tp", 0),
            "Cut Loss": sig.get("suggested_sl", 0),
            "RR Ratio": sig.get("risk_reward", 0),
        })

        progress.progress((i + 1) / len(tickers))

    status.text("Done")
    st.session_state.scan_results = pd.DataFrame(results)


# ─────────────────────────────
# RENDER
# ─────────────────────────────
if st.session_state.scan_results is not None:

    df_result = st.session_state.scan_results

    if df_result.empty:
        st.warning("Tidak ada data valid")
        st.stop()

    st.subheader("📊 Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("BUY", (df_result["Signal"] == "BUY").sum())
    col2.metric("SELL", (df_result["Signal"] == "SELL").sum())
    col3.metric("HOLD", (df_result["Signal"] == "NEUTRAL").sum())

    st.dataframe(df_result, use_container_width=True)

else:
    st.info("Klik Scan Sekarang")
