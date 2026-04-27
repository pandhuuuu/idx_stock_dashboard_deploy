import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS
)

from ai_model import train_model, predict_signal

st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

# ─────────────────────────────
# SIDEBAR
# ─────────────────────────────
st.sidebar.title("⚙️ Settings")

tickers_input = st.sidebar.text_area(
    "Kode Saham",
    ",".join(DEFAULT_TICKERS[:8])
)

period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y"])
interval = st.sidebar.selectbox("Interval", ["1d", "1wk"])

run_button = st.sidebar.button("🚀 Scan")

# AUTO REFRESH
if st.sidebar.checkbox("🔄 Auto Refresh"):
    st_autorefresh(interval=60000, key="refresh")

# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 AI Trading Dashboard")
st.caption("Technical + AI Prediction")

# ─────────────────────────────
# SCAN
# ─────────────────────────────
if run_button:

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    results = []

    for ticker in tickers:

        df = fetch_data(add_jk(ticker), period=period, interval=interval)

        if df is not None:

            sig = calculate_signals(df)

            # 🔥 AI PART
            model = train_model(df)
            ai_prob = predict_signal(model, df)

            if ai_prob > 0.6:
                ai_signal = "AI BUY"
            elif ai_prob < 0.4:
                ai_signal = "AI SELL"
            else:
                ai_signal = "AI HOLD"

            # NORMAL SIGNAL
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
                "Signal": signal,
                "AI Prob UP": round(ai_prob * 100, 2),
                "AI Signal": ai_signal,
                "Confidence": sig["confidence"]
            })

    df_result = pd.DataFrame(results)

    # ─────────────────────────────
    # TABLE
    # ─────────────────────────────
    st.subheader("📈 Market Scanner")
    st.dataframe(df_result, use_container_width=True)

    # ─────────────────────────────
    # AI PANEL
    # ─────────────────────────────
    st.subheader("🤖 AI Prediction")

    selected_ai = st.selectbox("Pilih saham", df_result["Saham"])

    row = df_result[df_result["Saham"] == selected_ai].iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("AI Prob UP (%)", row["AI Prob UP"])
    col2.metric("AI Signal", row["AI Signal"])
    col3.metric("Confidence", row["Confidence"])

    # ─────────────────────────────
    # CHART
    # ─────────────────────────────
    st.subheader("📉 Chart")

    df_chart = fetch_data(add_jk(selected_ai), period=period, interval=interval)

    if df_chart is not None:

        df_chart["MA10"] = df_chart["Close"].rolling(10).mean()
        df_chart["MA30"] = df_chart["Close"].rolling(30).mean()

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df_chart.index,
            open=df_chart['Open'],
            high=df_chart['High'],
            low=df_chart['Low'],
            close=df_chart['Close']
        ))

        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MA10"], name="MA10"))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MA30"], name="MA30"))

        st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Last update: {datetime.now()}")
