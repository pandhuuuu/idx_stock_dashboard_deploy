import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import yfinance as yf
import pytz  # ✅ TAMBAHAN WAJIB

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
# AUTO MARKET REFRESH SYSTEM (NEW)
# ─────────────────────────────
def get_refresh_interval():
    tz = pytz.timezone("Asia/Jakarta")
    now = datetime.now(tz)

    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    if weekday >= 5:
        return 120  # weekend

    current_time = hour + minute / 60

    if 9 <= current_time < 12:
        return 15   # market aktif
    if 12 <= current_time < 13.5:
        return 60   # lunch break
    if 13.5 <= current_time < 15:
        return 15   # sesi 2

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

period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "10y"], index=1)
interval = st.sidebar.selectbox("Interval", ["1min", "5min", "1d", "1wk", "1mo"], index=0)

run_button = st.sidebar.button("🚀 Scan Sekarang Atau Besok")
auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh")


# ─────────────────────────────
# FIXED AUTO REFRESH (NO 15000 BUG)
# ─────────────────────────────
if auto_refresh:
    try:
        refresh_interval = get_refresh_interval()

        st.sidebar.info(f"⏱️ Refresh: {refresh_interval} detik")

        if refresh_interval == 15:
            st.sidebar.success("🟢 Market Aktif")
        elif refresh_interval == 60:
            st.sidebar.warning("🟡 Market Istirahat")
        else:
            st.sidebar.info("🔵 Weekend Mode")

        st_autorefresh(
            interval=refresh_interval * 1000,
            key="auto_refresh"
        )

    except:
        st.warning("Auto refresh error")


# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 MASA GAK ALL-IN 🤔")
st.title("CACING-CACING 🪱 NAGA-NAGA 🐉🔥")


# ─────────────────────────────
# CHART (FULL ORIGINAL KAMU - FIXED SYNTAX ONLY)
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
        ma10_prev = df['MA10'].iloc[i - 1]
        ma30_now = df['MA30'].iloc[i]
        ma30_prev = df['MA30'].iloc[i - 1]
        rsi_now = df['RSI'].iloc[i]

        if any(v != v for v in [ma10_now, ma10_prev, ma30_now, ma30_prev]):
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

    fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='MA10'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA30'], name='MA30'))

    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        title=f"{ticker} | {signal}"
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

    df_result["Action"] = df_result["Signal"].apply(lambda x: "HOLD" if x == "NEUTRAL" else x)

    st.subheader("📊 Market Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("BUY", (df_result["Signal"] == "BUY").sum())
    col2.metric("SELL", (df_result["Signal"] == "SELL").sum())
    col3.metric("HOLD", (df_result["Action"] == "HOLD").sum())

    st.subheader("📈 Market Scanner")

    df_display = df_result.copy()
    df_display["Signal"] = df_display["Signal"].apply(format_signal)

    st.dataframe(df_display, use_container_width=True)

    st.subheader("📉 Chart")

    selected = st.selectbox("Pilih Saham", df_result["Saham"])

    row = df_result[df_result["Saham"] == selected].iloc[0]
    df_chart = fetch_data(add_jk(selected), period=period, interval=interval)

    if df_chart is not None:
        fig = plot_candlestick_with_signal(df_chart, selected, row["Signal"])
        st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Last update: {datetime.now()}")

else:
    st.info("Klik Scan atau aktifkan Auto Refresh")
