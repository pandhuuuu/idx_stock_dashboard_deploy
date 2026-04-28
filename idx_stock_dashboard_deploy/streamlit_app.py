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
        tickers_source = get_all_idx_tickers()
        if not tickers_source:
            tickers_source = DEFAULT_TICKERS
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
st.title("📊 IDX STOCK DASHBOARD")


# ─────────────────────────────
# MAIN SCAN (FIXED)
# ─────────────────────────────
if run_button or auto_refresh:

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    results = []

    progress = st.progress(0)
    status = st.empty()

    total = len(tickers)

    for i, ticker in enumerate(tickers):
        status.text(f"Scanning {ticker}...")

        df = cached_fetch(add_jk(ticker), period, interval)

        # ✅ FIX 1: df invalid skip
        if df is None or df.empty:
            progress.progress((i + 1) / total)
            continue

        sig = calculate_signals(df)

        # ✅ FIX 2: sig None skip (INI PENYEBAB ERROR KAMU)
        if sig is None:
            progress.progress((i + 1) / total)
            continue

        # ── LOGIC ASLI KAMU (TIDAK DIUBAH) ──
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
            "RSI": round(sig["rsi"], 2),
            "Signal": signal,
            "Confidence": sig["confidence"],
            "Entry": sig["price"],
            "Take Profit": round(sig["suggested_tp"], 2),
            "Cut Loss": round(sig["suggested_sl"], 2),
            "RR Ratio": round(sig["risk_reward"], 2),
        })

        progress.progress((i + 1) / total)

    status.text("✅ Scan selesai!")

    st.session_state.scan_results = pd.DataFrame(results)


# ─────────────────────────────
# RENDER HASIL
# ─────────────────────────────
if st.session_state.scan_results is not None:

    df_result = st.session_state.scan_results.copy()

    if df_result.empty:
        st.warning("Tidak ada data yang valid")
        st.stop()

    df_result["Action"] = df_result["Signal"].apply(
        lambda x: "HOLD" if x == "NEUTRAL" else x
    )

    st.subheader("📊 Market Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🟢 BUY", (df_result["Signal"] == "BUY").sum())
    col2.metric("🔴 SELL", (df_result["Signal"] == "SELL").sum())
    col3.metric("⚪ HOLD", (df_result["Action"] == "HOLD").sum())
    col4.metric("📋 TOTAL", len(df_result))

    st.dataframe(df_result, use_container_width=True)

    st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

else:
    st.info("Klik **Scan Sekarang** untuk mulai")
