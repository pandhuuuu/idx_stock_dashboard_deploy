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
# COLOR HELPER (ADDED)
# ─────────────────────────────
def color_text(value, positive=True):
    color = "green" if positive else "red"
    return f"<span style='color:{color}; font-weight:600'>{value}</span>"


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
# CHART FUNCTION
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
            textposition="bottom center",
            marker=dict(size=12, symbol="triangle-up")
        ))

    elif signal == "SELL":
        fig.add_trace(go.Scatter(
            x=[last_date],
            y=[last_price],
            mode='markers+text',
            text=["SELL"],
            textposition="top center",
            marker=dict(size=12, symbol="triangle-down")
        ))

    fig.update_layout(height=500)
    return fig


# ─────────────────────────────
# SECTOR MAP
# ─────────────────────────────
sector_map = {
    "BANK": ["BBCA", "BBRI", "BMRI", "BNGA", "BRIS", "BTPS", "BBNI"],
    "ENERGY": ["ADRO", "PTBA", "PGAS", "MEDC", "ITMG", "INDY"],
    "GOLD / MINING": ["ANTM", "MDKA", "INCO", "BRMS", "PSAB"],
    "CONSUMER": ["UNVR", "ICBP", "INDF", "MYOR", "KLBF", "SIDO"],
    "TELECOM": ["TLKM", "EXCL", "ISAT"],
    "TECH": ["GOTO", "BUKA", "DCII", "WIFI"],
    "PROPERTY": ["BSDE", "PWON", "CTRA", "SMRA"],
}


# ─────────────────────────────
# MAIN LOGIC
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

                # COLOR STATE
                "Signal_Color": "green" if signal == "BUY" else "red" if signal == "SELL" else "gray",
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
    # SUMMARY (COLORIZED)
    # ─────────────────────────────
    st.subheader("📊 Market Summary")

    buy_val = (df_result["Signal"] == "BUY").sum()
    sell_val = (df_result["Signal"] == "SELL").sum()
    hold_val = (df_result["Action"] == "HOLD").sum()

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"### 🟢 BUY\n{color_text(buy_val, True)}", unsafe_allow_html=True)
    col2.markdown(f"### 🔴 SELL\n{color_text(sell_val, False)}", unsafe_allow_html=True)
    col3.markdown(f"### ⚪ HOLD\n{hold_val}")


    # ─────────────────────────────
    # SECTOR BREAKDOWN
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
    # MAIN TABLE (COLOR STYLE)
    # ─────────────────────────────
    st.subheader("📈 Market Scanner")

    styled_df = df_result.sort_values(by="Confidence", ascending=False)

    styled_df = styled_df.style.applymap(
        lambda v: "color: green; font-weight:600" if v == "BUY"
        else "color: red; font-weight:600" if v == "SELL"
        else "color: gray",
        subset=["Signal"]
    ).applymap(
        lambda v: "color: green" if v < 30 else "color: red" if v > 70 else "color: orange",
        subset=["RSI"]
    )

    st.dataframe(styled_df, use_container_width=True)


    # ─────────────────────────────
    # TOP SIGNALS
    # ─────────────────────────────
    st.subheader("🎯 Top Trading Signals")

    col_buy, col_sell = st.columns(2)

    top_buy = df_result[df_result["Signal"] == "BUY"]\
        .sort_values(by="Confidence", ascending=False).head(5)

    top_sell = df_result[df_result["Signal"] == "SELL"]\
        .sort_values(by="Confidence", ascending=False).head(5)

    with col_buy:
        st.markdown("### 🟢 Top BUY")
        st.dataframe(top_buy, use_container_width=True)

    with col_sell:
        st.markdown("### 🔴 Top SELL")
        st.dataframe(top_sell, use_container_width=True)


    # ─────────────────────────────
    # TRADING PLAN
    # ─────────────────────────────
    st.subheader("💰 Trading Plan")

    plan_df = df_result[[
        "Saham", "Sektor", "Harga", "Entry",
        "Take Profit", "Cut Loss", "RR Ratio",
        "Action", "Confidence"
    ]].sort_values(by="Confidence", ascending=False)

    st.dataframe(plan_df, use_container_width=True)


    # ─────────────────────────────
    # SECTOR TABLES
    # ─────────────────────────────
    st.subheader("🏭 Sector-Based Tables")

    for sector_name, sector_list in sector_map.items():

        sector_df = df_result[df_result["Saham"].isin(sector_list)]

        if not sector_df.empty:
            st.markdown(f"### 📌 {sector_name}")
            st.dataframe(
                sector_df.sort_values(by="Confidence", ascending=False),
                use_container_width=True
            )


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


    st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.warning("⚠️ Not financial advice")

else:
    st.info("Klik Scan atau aktifkan Auto Refresh")
