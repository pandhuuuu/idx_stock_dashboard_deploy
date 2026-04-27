import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
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
# AUTO MARKET REFRESH SYSTEM
# ─────────────────────────────
def get_refresh_interval():
    tz = pytz.timezone("Asia/Jakarta")
    now = datetime.now(tz)

    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    # Weekend
    if weekday >= 5:
        return 120

    current_time = hour + minute / 60

    # Market session 1
    if 9 <= current_time < 12:
        return 15

    # Lunch break
    if 12 <= current_time < 13.5:
        return 60

    # Market session 2
    if 13.5 <= current_time < 15:
        return 15

    # After market
    return 60


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
# FORMAT
# ─────────────────────────────
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
    "Kode Saham (pisah koma)",
    ",".join(tickers_source[:30])
)

period = st.sidebar.selectbox(
    "Period", ["1mo", "3mo", "6mo", "1y"], index=1
)

interval = st.sidebar.selectbox(
    "Interval", ["1d", "1wk", "1mo"], index=0
)

run_button = st.sidebar.button("🚀 Scan")

auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh")

# ─────────────────────────────
# AUTO REFRESH ENGINE (FIXED)
# ─────────────────────────────
refresh_interval = get_refresh_interval()

if auto_refresh:
    st.sidebar.info(f"⏱️ Refresh: {refresh_interval} detik")

    if refresh_interval == 15:
        st.sidebar.success("🟢 Market Aktif")
    elif refresh_interval == 60:
        st.sidebar.warning("🟡 Market Tutup / Istirahat")
    else:
        st.sidebar.info("🔵 Weekend Mode")

    st_autorefresh(
        interval=refresh_interval * 1000,
        key="auto_refresh"
    )


# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 IDX Stock Dashboard")
st.caption("Auto Adaptive Market Scanner (Pro Mode)")


# ─────────────────────────────
# MAIN EXECUTION
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
                "TP": sig["suggested_tp"],
                "SL": sig["suggested_sl"],
                "RR": sig["risk_reward"],
            })

        progress.progress((i + 1) / len(tickers))

    status.text("✅ Scan selesai")

    df_result = pd.DataFrame(results)

    if df_result.empty:
        st.error("Tidak ada data")
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
    st.subheader("📈 Signal Table")

    df_display = df_result.copy()
    df_display["Signal"] = df_display["Signal"].apply(format_signal)

    st.dataframe(
        df_display.sort_values("Confidence", ascending=False),
        use_container_width=True
    )

    # ─────────────────────────────
    # TOP PICKS
    # ─────────────────────────────
    st.subheader("🔥 Top BUY")

    st.dataframe(
        df_result[df_result["Signal"] == "BUY"]
        .sort_values("Confidence", ascending=False)
        .head(5),
        use_container_width=True
    )

    st.subheader("⚠️ Top SELL")

    st.dataframe(
        df_result[df_result["Signal"] == "SELL"]
        .sort_values("Confidence", ascending=False)
        .head(5),
        use_container_width=True
    )

    st.caption(f"Last update: {datetime.now()}")

else:
    st.info("Klik Scan atau aktifkan Auto Refresh")
