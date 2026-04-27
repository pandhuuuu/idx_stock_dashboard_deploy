import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# IMPORT LOGIC KAMU
from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS
)

st.set_page_config(
    page_title="IDX Stock Dashboard",
    layout="wide"
)

# ─────────────────────────────
# SIDEBAR
# ─────────────────────────────
st.sidebar.title("⚙️ Settings")

tickers_input = st.sidebar.text_area(
    "Kode Saham (pisah koma)",
    ",".join(DEFAULT_TICKERS[:10])
)

period = st.sidebar.selectbox(
    "Period",
    ["1mo", "3mo", "6mo", "1y"],
    index=1
)

interval = st.sidebar.selectbox(
    "Interval",
    ["1d", "1wk"],
    index=0
)

run_button = st.sidebar.button("🚀 Scan Sekarang")

# AUTO REFRESH
auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh")
refresh_interval = st.sidebar.slider("Interval (detik)", 10, 300, 60)

if auto_refresh:
    st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")

# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 IDX Stock Entry Signal Dashboard")
st.caption("Multi-Factor Technical Analysis (MA, RSI, MACD, BB, Volume)")

# ─────────────────────────────
# TRIGGER SCAN
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
                "Harga": sig["price"],
                "RSI": sig["rsi"],
                "Stoch": sig["stoch_k"],
                "Volume(x)": sig["vol_ratio"],
                "ATR %": sig["atr_pct"],
                "Signal": signal,
                "Bull Score": sig["bull_score"],
                "Bear Score": sig["bear_score"],
                "Confidence": sig["confidence"],
            })
        else:
            results.append({
                "Saham": ticker,
                "Harga": "-",
                "RSI": "-",
                "Stoch": "-",
                "Volume(x)": "-",
                "ATR %": "-",
                "Signal": "NO DATA",
                "Bull Score": 0,
                "Bear Score": 0,
                "Confidence": 0,
            })

        progress.progress((i + 1) / len(tickers))

    status.text("✅ Scan selesai!")

    df_result = pd.DataFrame(results)

    # ─────────────────────────────
    # SUMMARY
    # ─────────────────────────────
    st.subheader("📊 Market Summary")

    col1, col2, col3 = st.columns(3)

    buy_count = len(df_result[df_result["Signal"] == "BUY"])
    sell_count = len(df_result[df_result["Signal"] == "SELL"])
    neutral_count = len(df_result[df_result["Signal"] == "NEUTRAL"])

    col1.metric("BUY", buy_count)
    col2.metric("SELL", sell_count)
    col3.metric("NEUTRAL", neutral_count)

    # MARKET SENTIMENT
    total = len(df_result)
    if total > 0:
        buy_pct = buy_count / total * 100
        sell_pct = sell_count / total * 100

        if buy_pct > sell_pct + 10:
            sentiment = "🐂 BULLISH"
            color = "green"
        elif sell_pct > buy_pct + 10:
            sentiment = "🐻 BEARISH"
            color = "red"
        else:
            sentiment = "⚖️ NEUTRAL"
            color = "orange"

        st.markdown(f"### Market Sentiment: :{color}[{sentiment}]")

    # ─────────────────────────────
    # TABLE
    # ─────────────────────────────
    st.subheader("📈 Hasil Analisis")

    st.dataframe(
        df_result.sort_values(by="Confidence", ascending=False),
        use_container_width=True
    )

    # ─────────────────────────────
    # TOP SIGNAL
    # ─────────────────────────────
    st.subheader("🔥 Top Signals")

    colA, colB = st.columns(2)

    top_buy = df_result[df_result["Signal"] == "BUY"].sort_values(by="Confidence", ascending=False).head(5)
    top_sell = df_result[df_result["Signal"] == "SELL"].sort_values(by="Confidence", ascending=False).head(5)

    with colA:
        st.markdown("### 🟢 Top BUY")
        st.dataframe(top_buy, use_container_width=True)

    with colB:
        st.markdown("### 🔴 Top SELL")
        st.dataframe(top_sell, use_container_width=True)

    # ─────────────────────────────
    # FOOTER
    # ─────────────────────────────
    st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.warning("⚠️ Not financial advice. For educational purposes only.")

else:
    st.info("Klik **Scan Sekarang** atau aktifkan Auto Refresh di sidebar.")
