import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

# IMPORT LOGIC
from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS
)

st.set_page_config(page_title="IDX Stock Dashboard", layout="wide")

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

# AUTO REFRESH (AMAN)
auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh")
refresh_interval = st.sidebar.slider("Interval (detik)", 10, 300, 60)

if auto_refresh:
    try:
        st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")
    except:
        st.warning("Autorefresh module belum terinstall")

# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 IDX Stock Entry Signal Dashboard")
st.caption("Multi-Factor Technical Analysis")

# ─────────────────────────────
# FUNCTION CHART
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

    # MA
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA30'] = df['Close'].rolling(30).mean()

    fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='MA10'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA30'], name='MA30'))

    # Signal marker
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

    fig.update_layout(
        title=f"{ticker} Chart ({signal})",
        height=500
    )

    return fig


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

    # SAFETY FIX (anti error kosong)
    if df_result.empty or "Confidence" not in df_result.columns:
        st.error("❌ Tidak ada data. Cek ticker atau koneksi API.")
        st.stop()

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

    # ─────────────────────────────
    # TABLE
    # ─────────────────────────────
    st.subheader("📈 Hasil Analisis")

    st.dataframe(
        df_result.sort_values(by="Confidence", ascending=False),
        use_container_width=True
    )

    # ─────────────────────────────
    # 🔥 REKOMENDASI
    # ─────────────────────────────
    st.subheader("🎯 Rekomendasi Trading")

    col_buy, col_sell = st.columns(2)

    top_buy = df_result[df_result["Signal"] == "BUY"]\
        .sort_values(by="Confidence", ascending=False).head(5)

    top_sell = df_result[df_result["Signal"] == "SELL"]\
        .sort_values(by="Confidence", ascending=False).head(5)

    with col_buy:
        st.markdown("### 🟢 Top BUY")
        if not top_buy.empty:
            st.dataframe(top_buy, use_container_width=True)
        else:
            st.info("Tidak ada sinyal BUY")

    with col_sell:
        st.markdown("### 🔴 Top SELL")
        if not top_sell.empty:
            st.dataframe(top_sell, use_container_width=True)
        else:
            st.info("Tidak ada sinyal SELL")

    # ─────────────────────────────
    # CHART
    # ─────────────────────────────
    st.subheader("📉 Chart Saham")

    selected_ticker = st.selectbox(
        "Pilih saham",
        df_result["Saham"]
    )

    selected_row = df_result[df_result["Saham"] == selected_ticker].iloc[0]

    df_chart = fetch_data(add_jk(selected_ticker), period=period, interval=interval)

    if df_chart is not None:
        fig = plot_candlestick_with_signal(
            df_chart,
            selected_ticker,
            selected_row["Signal"]
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Data tidak tersedia")

    # ─────────────────────────────
    # FOOTER
    # ─────────────────────────────
    st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.warning("⚠️ Not financial advice")

else:
    st.info("Klik **Scan Sekarang** atau aktifkan Auto Refresh.")
