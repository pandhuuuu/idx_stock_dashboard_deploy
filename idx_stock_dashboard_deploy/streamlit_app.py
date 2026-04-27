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
    ",".join(tickers_source[:10])
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
# CHART
# ─────────────────────────────
def plot_candlestick_with_signal(df, ticker, signal):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price'
    ))

    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA30'] = df['Close'].rolling(30).mean()

    fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='MA10'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA30'], name='MA30'))

    last_price = df['Close'].iloc[-1]
    last_date = df.index[-1]

    if signal == "BUY":
        fig.add_trace(go.Scatter(
            x=[last_date],
            y=[last_price],
            mode='markers+text',
            text=["BUY"],
            marker=dict(size=12, symbol="triangle-up")
        ))

    elif signal == "SELL":
        fig.add_trace(go.Scatter(
            x=[last_date],
            y=[last_price],
            mode='markers+text',
            text=["SELL"],
            marker=dict(size=12, symbol="triangle-down")
        ))

    fig.update_layout(height=500)
    return fig


# ─────────────────────────────
# SECTOR MAP
# ─────────────────────────────
sector_map = {
    "BANK": ["BBCA", "BBRI", "BMRI", "BNGA", "BRIS", "BBNI"],
    "ENERGY": ["ADRO", "PTBA", "PGAS", "MEDC", "ITMG"],
    "MINING": ["ANTM", "MDKA", "INCO", "BRMS"],
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
