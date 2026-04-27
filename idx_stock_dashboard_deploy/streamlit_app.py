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

# SECTOR MAPPING

# ─────────────────────────────

SECTOR_MAP = {
# BANK
"BBCA": "Bank", "BBRI": "Bank", "BMRI": "Bank", "BBNI": "Bank", "BRIS": "Bank",

```
# TELEKOM
"TLKM": "Telekomunikasi", "EXCL": "Telekomunikasi", "ISAT": "Telekomunikasi",

# CONSUMER
"ICBP": "Consumer", "INDF": "Consumer", "UNVR": "Consumer", "MYOR": "Consumer",

# ENERGY
"ADRO": "Energy", "PTBA": "Energy", "MEDC": "Energy", "PGAS": "Energy",

# MINING
"ANTM": "Mining", "INCO": "Mining", "MDKA": "Mining",

# PROPERTY
"BSDE": "Property", "CTRA": "Property", "PWON": "Property",

# INFRA
"JSMR": "Infrastructure", "WIKA": "Infrastructure", "PTPP": "Infrastructure",

# HEALTH
"MIKA": "Healthcare", "SILO": "Healthcare", "HEAL": "Healthcare",

# RETAIL
"ACES": "Retail", "AMRT": "Retail", "MAPI": "Retail",
```

}

# ─────────────────────────────

# SIDEBAR

# ─────────────────────────────

st.sidebar.title("⚙️ Settings")

tickers_input = st.sidebar.text_area(
"Kode Saham (pisah koma)",
",".join(DEFAULT_TICKERS[:15])
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
try:
st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")
except:
st.warning("Module autorefresh belum terinstall")

# ─────────────────────────────

# HEADER

# ─────────────────────────────

st.title("📊 IDX Trading Dashboard PRO")
st.caption("Scanner + Trading Plan + Chart + Sector Analysis")

# ─────────────────────────────

# FUNCTION CHART

# ─────────────────────────────

def plot_candlestick_with_signal(df, ticker, signal):
fig = go.Figure()

```
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name='Price'
))

# Moving Average
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
```

# ─────────────────────────────

# MAIN LOGIC

# ─────────────────────────────

if run_button or auto_refresh:

```
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
results = []

progress = st.progress(0)
status = st.empty()

for i, ticker in enumerate(tickers):
    status.text(f"Scanning {ticker}...")

    df = fetch_data(add_jk(ticker), period=period, interval=interval)

    if df is not None:
        sig = calculate_signals(df)

        # SIGNAL
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
            "Confidence": sig["confidence"],

            # TRADING PLAN
            "Entry": sig["price"],
            "Take Profit": sig["suggested_tp"],
            "Cut Loss": sig["suggested_sl"],
            "RR Ratio": sig["risk_reward"],
        })

    progress.progress((i + 1) / len(tickers))

status.text("✅ Scan selesai!")

df_result = pd.DataFrame(results)

if df_result.empty:
    st.error("❌ Tidak ada data. Cek ticker atau koneksi.")
    st.stop()

# ACTION
df_result["Action"] = df_result["Signal"].apply(
    lambda x: "HOLD" if x == "NEUTRAL" else x
)

# SECTOR
df_result["Sector"] = df_result["Saham"].map(SECTOR_MAP).fillna("Others")

# ─────────────────────────────
# SUMMARY
# ─────────────────────────────
st.subheader("📊 Market Summary")

col1, col2, col3 = st.columns(3)

col1.metric("BUY", (df_result["Signal"] == "BUY").sum())
col2.metric("SELL", (df_result["Signal"] == "SELL").sum())
col3.metric("HOLD", (df_result["Action"] == "HOLD").sum())

# ─────────────────────────────
# TABLE PER SEKTOR
# ─────────────────────────────
st.subheader("📊 Market Scanner by Sector")

sectors = df_result["Sector"].unique()

for sector in sorted(sectors):
    sector_df = df_result[df_result["Sector"] == sector]\
        .sort_values(by="Confidence", ascending=False)

    if not sector_df.empty:
        with st.expander(f"🏭 {sector} ({len(sector_df)} saham)"):
            st.dataframe(sector_df, use_container_width=True)

# ─────────────────────────────
# TOP SIGNAL
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
st.subheader("💰 Trading Plan Recommendation")

plan_df = df_result[[
    "Saham",
    "Harga",
    "Entry",
    "Take Profit",
    "Cut Loss",
    "RR Ratio",
    "Action",
    "Confidence"
]].sort_values(by="Confidence", ascending=False)

st.dataframe(plan_df, use_container_width=True)

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
else:
    st.warning("Data chart tidak tersedia")

# ─────────────────────────────
# FOOTER
# ─────────────────────────────
st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.warning("⚠️ Not financial advice")
```

else:
st.info("Klik Scan atau aktifkan Auto Refresh")
