import streamlit as st
import pandas as pd
import numpy as np
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
# CUSTOM CSS (dark card style)
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
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 20px;
        width: 100%;
    }
    .stButton > button:hover { opacity: 0.9; }

    .stDownloadButton > button {
        background: #1a2a1a;
        color: #4caf50;
        border: 1px solid #4caf50;
        border-radius: 8px;
        font-weight: 600;
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
# CACHED FETCH (5 menit)
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
# 🔮 FUTURE PREDICTION FUNCTION (FIX ERROR)
# ─────────────────────────────
def predict_future(df, days=30):
    df = df.copy()

    df = df[['Close']].dropna()
    df['x'] = np.arange(len(df))

    x = df['x'].values
    y = df['Close'].values

    slope, intercept = np.polyfit(x, y, 1)

    last_x = x[-1]
    future_x = np.arange(last_x + 1, last_x + days + 1)
    future_y = slope * future_x + intercept

    last_date = df.index[-1]
    future_dates = pd.date_range(last_date, periods=days + 1, freq="D")[1:]

    return future_dates, future_y

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

tickers_input    = st.sidebar.text_area("Kode Saham (pisah koma)", ",".join(tickers_source[:30]))
period           = st.sidebar.selectbox("Period",   ["1mo", "3mo", "6mo", "1y"], index=1)
interval         = st.sidebar.selectbox("Interval", ["1d", "1wk"], index=0)
run_button       = st.sidebar.button("🚀 Scan Sekarang")
auto_refresh     = st.sidebar.checkbox("🔄 Auto Refresh")
refresh_interval = st.sidebar.slider("Interval (detik)", 10, 300, 60)

if auto_refresh:
    try:
        st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh")
    except:
        st.warning("Module autorefresh belum terinstall")

# Watchlist
st.sidebar.markdown("---")
st.sidebar.markdown("### ⭐ Watchlist")
add_watch = st.sidebar.text_input("Tambah ke Watchlist", placeholder="Contoh: BBCA")
if st.sidebar.button("➕ Tambah") and add_watch.strip():
    ticker_up = add_watch.strip().upper()
    if ticker_up not in st.session_state.watchlist:
        st.session_state.watchlist.append(ticker_up)
        st.toast(f"✅ {ticker_up} ditambahkan ke watchlist!")

if st.session_state.watchlist:
    for w in st.session_state.watchlist:
        col_w1, col_w2 = st.sidebar.columns([3, 1])
        col_w1.markdown(f"**{w}**")
        if col_w2.button("✕", key=f"rm_{w}"):
            st.session_state.watchlist.remove(w)
            st.rerun()
else:
    st.sidebar.caption("Belum ada saham di watchlist")


# ─────────────────────────────
# HEADER
# ─────────────────────────────
st.title("📊 MASA GAK ALL-IN 🤔")
st.title("CACING-CACING 🪱  NAGA-NAGA𓆩 🐉 🔥🔥🔥")


# ─────────────────────────────
# CHART FUNCTION
# ─────────────────────────────
def plot_candlestick_with_signal(df, ticker, signal):
    df = df.copy()

    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA30'] = df['Close'].rolling(30).mean()

    # RSI manual
    delta = df['Close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float('nan'))
    df['RSI'] = 100 - (100 / (1 + rs))

    # Historical buy/sell dari MA crossover
    buy_dates, buy_prices   = [], []
    sell_dates, sell_prices = [], []

    for i in range(1, len(df)):
        ma10_now  = df['MA10'].iloc[i]
        ma10_prev = df['MA10'].iloc[i - 1]
        ma30_now  = df['MA30'].iloc[i]
        ma30_prev = df['MA30'].iloc[i - 1]
        rsi_now   = df['RSI'].iloc[i]

        if any(v != v for v in [ma10_now, ma10_prev, ma30_now, ma30_prev]):
            continue

        if ma10_now > ma30_now and ma10_prev <= ma30_prev and rsi_now < 60:
            buy_dates.append(df.index[i])
            buy_prices.append(df['Low'].iloc[i] * 0.985)
        elif ma10_now < ma30_now and ma10_prev >= ma30_prev and rsi_now > 40:
            sell_dates.append(df.index[i])
            sell_prices.append(df['High'].iloc[i] * 1.015)

    # Swing points
    window    = 5
    lows_idx  = []
    highs_idx = []
    for i in range(window, len(df) - window):
        if df['Low'].iloc[i]  == df['Low'].iloc[i - window: i + window + 1].min():
            lows_idx.append(i)
        if df['High'].iloc[i] == df['High'].iloc[i - window: i + window + 1].max():
            highs_idx.append(i)

    # 3 panel: candle | volume | RSI
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.02,
        subplot_titles=("", "Volume", "RSI (14)")
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'],   close=df['Close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
    ), row=1, col=1)

    # MA
    fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='MA10',
        line=dict(color='#2196F3', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA30'], name='MA30',
        line=dict(color='#FF9800', width=1.5)), row=1, col=1)

    # Trendline
    if len(lows_idx) >= 2:
        x_pts = lows_idx[-5:]
        y_pts = [df['Low'].iloc[i] for i in x_pts]
        n     = len(x_pts)
        xm    = sum(x_pts) / n
        ym    = sum(y_pts) / n
        denom = sum((x_pts[i] - xm) ** 2 for i in range(n))
        if denom != 0:
            slope     = sum((x_pts[i] - xm) * (y_pts[i] - ym) for i in range(n)) / denom
            intercept = ym - slope * xm
            fig.add_trace(go.Scatter(
                x=[df.index[0], df.index[-1]],
                y=[intercept, intercept + slope * (len(df) - 1)],
                name='Trendline', mode='lines',
                line=dict(color='#FF5252', width=1.5, dash='dot')
            ), row=1, col=1)

    # Support
    for idx in lows_idx[-3:]:
        fig.add_hline(y=df['Low'].iloc[idx], line_width=1, line_dash='dash',
                      line_color='#1565C0',
                      annotation_text=f"S {df['Low'].iloc[idx]:,.0f}",
                      annotation_font=dict(color='#1565C0', size=9),
                      annotation_position='right', row=1, col=1)

    # Resistance
    for idx in highs_idx[-3:]:
        fig.add_hline(y=df['High'].iloc[idx], line_width=1, line_dash='dash',
                      line_color='#B71C1C',
                      annotation_text=f"R {df['High'].iloc[idx]:,.0f}",
                      annotation_font=dict(color='#B71C1C', size=9),
                      annotation_position='right', row=1, col=1)

    # Buy markers
    if buy_dates:
        fig.add_trace(go.Scatter(
            x=buy_dates, y=buy_prices, mode='markers', name='Buy Signal',
            marker=dict(symbol='triangle-up', size=14, color='#00C853',
                        line=dict(color='#007E33', width=1)),
            hovertemplate='<b>Buy-point</b><br>%{x}<extra></extra>'
        ), row=1, col=1)
        for d, p in zip(buy_dates, buy_prices):
            fig.add_annotation(x=d, y=p, text="Buy-point",
                showarrow=True, arrowhead=2, arrowcolor='#00C853',
                ax=0, ay=30, bgcolor='#00C853', bordercolor='#007E33',
                borderwidth=1, borderpad=3, font=dict(color='white', size=9),
                opacity=0.9, row=1, col=1)

    # Sell markers
    if sell_dates:
        fig.add_trace(go.Scatter(
            x=sell_dates, y=sell_prices, mode='markers', name='Sell Signal',
            marker=dict(symbol='triangle-down', size=14, color='#F44336',
                        line=dict(color='#B71C1C', width=1)),
            hovertemplate='<b>Sell-point</b><br>%{x}<extra></extra>'
        ), row=1, col=1)
        for d, p in zip(sell_dates, sell_prices):
            fig.add_annotation(x=d, y=p, text="Sell-point",
                showarrow=True, arrowhead=2, arrowcolor='#F44336',
                ax=0, ay=-30, bgcolor='#F44336', bordercolor='#B71C1C',
                borderwidth=1, borderpad=3, font=dict(color='white', size=9),
                opacity=0.9, row=1, col=1)

    # Volume
    if 'Volume' in df.columns:
        vol_colors = [
            '#26a69a' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef5350'
            for i in range(len(df))
        ]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'], name='Volume',
            marker_color=vol_colors, opacity=0.6, showlegend=False
        ), row=2, col=1)

    # RSI
    fig.add_trace(go.Scatter(
        x=df.index, y=df['RSI'], name='RSI',
        line=dict(color='#AB47BC', width=1.5), showlegend=False
    ), row=3, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor='#ef5350', opacity=0.08,
                  line_width=0, row=3, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor='#26a69a', opacity=0.08,
                  line_width=0, row=3, col=1)
    fig.add_hline(y=70, line_width=1, line_dash='dash',
                  line_color='#ef5350', opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_width=1, line_dash='dash',
                  line_color='#26a69a', opacity=0.5, row=3, col=1)

    signal_emoji = '🟢 BUY' if signal == 'BUY' else '🔴 SELL' if signal == 'SELL' else '⚪ NEUTRAL'

    fig.update_layout(
        height=620,
        title=f"<b>{ticker}</b>  |  {signal_emoji}",
        xaxis_rangeslider_visible=False,
        plot_bgcolor='#131722',
        paper_bgcolor='#131722',
        font=dict(color='#D1D4DC'),
        legend=dict(orientation='h', x=0, y=1.04,
                    bgcolor='rgba(0,0,0,0)', font=dict(size=10)),
        margin=dict(l=50, r=80, t=60, b=20),
        hovermode='x unified',
    )
    fig.update_xaxes(gridcolor='#1e2535', showgrid=True, zeroline=False)
    fig.update_yaxes(gridcolor='#1e2535', showgrid=True, zeroline=False, tickformat=',')
    fig.update_yaxes(range=[0, 100], row=3, col=1)

    return fig


# ─────────────────────────────
# SECTOR MAP
# ─────────────────────────────
sector_map = {
    "BANK":     ["BBCA", "BBRI", "BMRI", "BNGA", "BRIS", "BBNI"],
    "ENERGY":   ["ADRO", "PTBA", "PGAS", "MEDC", "ITMG"],
    "MINING":   ["ANTM", "MDKA", "INCO", "BRMS"],
    "CONSUMER": ["UNVR", "ICBP", "INDF", "MYOR"],
    "TELECOM":  ["TLKM", "EXCL", "ISAT"],
    "TECH":     ["GOTO", "WIFI"],
}


# ─────────────────────────────
# MAIN SCAN
# ─────────────────────────────
if run_button or auto_refresh:

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    results = []

    progress = st.progress(0)
    status   = st.empty()

    for i, ticker in enumerate(tickers):
        status.text(f"Scanning {ticker}...")
        df = cached_fetch(add_jk(ticker), period, interval)

        if df is not None:
            sig = calculate_signals(df)

            # ── SAFE GUARD ──
            if sig is None:
                continue
            
            if not isinstance(sig, dict):
                continue
            
            required_keys = ["bull_score", "bear_score", "price", "rsi"]
            if not all(k in sig for k in required_keys):
                continue
            
            # ── LOGIC ASLI KAMU (TIDAK DIUBAH) ──
            if sig["bull_score"] > sig["bear_score"] + 1:
                signal = "BUY"
            elif sig["bear_score"] > sig["bull_score"] + 1:
                signal = "SELL"
            else:
                signal = "NEUTRAL"

            results.append({
                "Saham":       ticker,
                "Sektor":      get_sector(ticker),
                "Harga":       sig["price"],
                "RSI":         round(sig["rsi"], 2),
                "Signal":      signal,
                "Confidence":  sig["confidence"],
                "Entry":       sig["price"],
                "Take Profit": round(sig["suggested_tp"], 2),
                "Cut Loss":    round(sig["suggested_sl"], 2),
                "RR Ratio":    round(sig["risk_reward"], 2),
            })

        progress.progress((i + 1) / len(tickers))

    status.text("✅ Scan selesai!")
    st.session_state.scan_results = pd.DataFrame(results)


# ─────────────────────────────
# RENDER HASIL
# ─────────────────────────────
if st.session_state.scan_results is not None:
    df_result = st.session_state.scan_results.copy()

    if df_result.empty:
        st.error("❌ Tidak ada data")
        st.stop()

    df_result["Action"] = df_result["Signal"].apply(
        lambda x: "HOLD" if x == "NEUTRAL" else x
    )

    # Market Summary
    st.subheader("📊 Market Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🟢 BUY",       (df_result["Signal"] == "BUY").sum())
    col2.metric("🔴 SELL",      (df_result["Signal"] == "SELL").sum())
    col3.metric("⚪ HOLD",      (df_result["Action"] == "HOLD").sum())
    col4.metric("📋 Total Scan", len(df_result))

    # Export CSV
    st.subheader("💾 Export Data")
    csv_data = df_result.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Hasil Scan (.csv)",
        data=csv_data,
        file_name=f"idx_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

    # Sector Breakdown
    st.subheader("🏭 Sector Breakdown")
    sector_df = df_result.groupby("Sektor").agg(
        Total=("Saham", "count"),
        Buy=("Signal",  lambda x: (x == "BUY").sum()),
        Sell=("Signal", lambda x: (x == "SELL").sum()),
        Hold=("Action", lambda x: (x == "HOLD").sum()),
    ).reset_index()
    st.dataframe(sector_df, use_container_width=True)

    # Market Scanner
    st.subheader("📈 Market Scanner")
    df_display         = df_result.copy()
    df_display["Signal"] = df_display["Signal"].apply(format_signal)
    st.dataframe(df_display.sort_values(by="Confidence", ascending=False),
                 use_container_width=True)

    # Top Signals
    st.subheader("🎯 Top Trading Signals")
    top_buy  = df_result[df_result["Signal"] == "BUY"].sort_values(
        by="Confidence", ascending=False).head(5).copy()
    top_sell = df_result[df_result["Signal"] == "SELL"].sort_values(
        by="Confidence", ascending=False).head(5).copy()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🟢 Top BUY")
        top_buy["Signal"] = top_buy["Signal"].apply(format_signal)
        st.dataframe(top_buy, use_container_width=True)
    with col2:
        st.markdown("### 🔴 Top SELL")
        top_sell["Signal"] = top_sell["Signal"].apply(format_signal)
        st.dataframe(top_sell, use_container_width=True)

    # Trading Plan
    st.subheader("💰 Trading Plan")
    plan_df = df_result[[
        "Saham", "Sektor", "Harga", "Entry", "Take Profit",
        "Cut Loss", "RR Ratio", "Action", "Confidence"
    ]].sort_values(by="Confidence", ascending=False).copy()
    plan_df["Action"] = plan_df["Action"].apply(format_signal)
    st.dataframe(plan_df, use_container_width=True)

    # Sector Tables
    st.subheader("🏭 Sector Tables")
    for sector, list_stock in sector_map.items():
        sdf = df_result[df_result["Saham"].isin(list_stock)].copy()
        if not sdf.empty:
            st.markdown(f"### {sector}")
            sdf["Signal"] = sdf["Signal"].apply(format_signal)
            st.dataframe(sdf, use_container_width=True)

    # Chart
    st.subheader("📉 Real Chart")

    # Watchlist shortcut buttons
    if st.session_state.watchlist:
        wl_intersect = [w for w in st.session_state.watchlist
                        if w in df_result["Saham"].values]
        if wl_intersect:
            st.caption("⭐ Watchlist kamu — klik untuk langsung lihat chart:")
            wl_cols = st.columns(len(wl_intersect))
            for i, w in enumerate(wl_intersect):
                if wl_cols[i].button(w, key=f"wl_chart_{w}"):
                    st.session_state["selected_chart"] = w

    saham_list  = df_result["Saham"].tolist()
    default_idx = 0
    if "selected_chart" in st.session_state and \
       st.session_state["selected_chart"] in saham_list:
        default_idx = saham_list.index(st.session_state["selected_chart"])

    selected = st.selectbox("Pilih Saham", saham_list, index=default_idx)
    st.session_state["selected_chart"] = selected

    row      = df_result[df_result["Saham"] == selected].iloc[0]
    df_chart = cached_fetch(add_jk(selected), period, interval)

    if df_chart is not None:
        fig = plot_candlestick_with_signal(df_chart, selected, row["Signal"])
        st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────────
    # 🔮 FUTURE PREDICTION CHART
    # ─────────────────────────────
    st.subheader("🔮 Prediction Future Chart (30 Hari)")

    df_future = cached_fetch(add_jk(selected), period, interval)

    if df_future is not None:
        future_dates, future_price = predict_future(df_future, 30)

        fig_pred = go.Figure()

        # Historical price
        fig_pred.add_trace(go.Scatter(
            x=df_future.index,
            y=df_future["Close"],
            name="Historical",
            line=dict(color="#2196F3")
        ))

        # Prediction line
        fig_pred.add_trace(go.Scatter(
            x=future_dates,
            y=future_price,
            name="Prediction 30D",
            line=dict(color="#FF9800", dash="dash")
        ))

        fig_pred.update_layout(
            height=450,
            title=f"<b>Future Prediction - {selected}</b>",
            plot_bgcolor='#131722',
            paper_bgcolor='#131722',
            font=dict(color='#D1D4DC'),
            hovermode="x unified"
        )

        st.plotly_chart(fig_pred, use_container_width=True)

    st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.warning("⚠️ Not financial advice. Gunakan sebagai referensi saja.")

else:
    st.info("👈 Klik **Scan Sekarang** atau aktifkan Auto Refresh untuk memulai.")
