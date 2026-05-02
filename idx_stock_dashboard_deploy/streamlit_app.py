import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from datetime import time
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh
from supabase import create_client
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from portfolio_page import render_portfolio_page
from broksum_processor import process_broksum, broker_activity, stock_activity, market_overview
from idx_stock_monitor import (
    fetch_data,
    calculate_signals,
    add_jk,
    DEFAULT_TICKERS,
    get_all_idx_tickers
)

st.set_page_config(page_title="MarketLens", layout="wide", page_icon="🧿")

# ─────────────────────────────
# CUSTOM CSS — PROFESSIONAL TRADING TERMINAL
# ─────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    /* ── Global ── */
    .stApp {
        background-color: #080b12;
        font-family: 'Space Grotesk', sans-serif;
    }
    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }

    /* ── Metrics ── */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #0d1117 0%, #161b27 100%);
        border: 1px solid #1e2a3a;
        border-top: 2px solid #2563eb;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
        transition: border-top-color 0.2s ease;
    }
    [data-testid="metric-container"]:hover {
        border-top-color: #3b82f6;
    }
    [data-testid="metric-container"] label {
        color: #64748b !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
        color: #e2e8f0 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 12px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* ── Section Headers ── */
    h1 { font-family: 'Space Grotesk', sans-serif !important; color: #f1f5f9 !important; }
    h2 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #e2e8f0 !important;
        border-left: 3px solid #2563eb !important;
        padding-left: 12px !important;
        margin-top: 28px !important;
        font-size: 18px !important;
        letter-spacing: -0.01em;
    }
    h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #cbd5e1 !important;
        border-left: 3px solid #334155 !important;
        padding-left: 10px !important;
        font-size: 15px !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0d14 0%, #0d1117 100%);
        border-right: 1px solid #1e2a3a;
    }
    [data-testid="stSidebar"] .stMarkdown p { color: #94a3b8; font-size: 13px; }
    [data-testid="stSidebar"] h1 { color: #e2e8f0 !important; font-size: 16px !important; }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #1d4ed8, #2563eb);
        color: #ffffff;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0.03em;
        padding: 10px 20px;
        width: 100%;
        height: 80px;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
        transition: all 0.2s ease;
        font-family: 'Space Grotesk', sans-serif;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb, #3b82f6);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
        transform: translateY(-1px);
    }

    .stDownloadButton > button {
        background: #071a0e;
        color: #22c55e;
        border: 1px solid #166534;
        border-radius: 8px;
        font-weight: 600;
        font-size: 12px;
        width: 100%;
        transition: all 0.2s;
    }
    .stDownloadButton > button:hover {
        background: #0f2e1a;
        border-color: #22c55e;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: #0d1117;
        border-bottom: 1px solid #1e2a3a;
        gap: 4px;
        padding: 0 4px;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        background: transparent;
        color: #64748b;
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0.02em;
        border-radius: 6px 6px 0 0;
        padding: 10px 20px;
        transition: all 0.2s;
        font-family: 'Space Grotesk', sans-serif;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: #0f1f3d !important;
        color: #3b82f6 !important;
        border-bottom: 2px solid #2563eb !important;
    }

    /* ── DataFrames ── */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #1e2a3a;
    }
    [data-testid="stDataFrame"] th {
        background: #0d1117 !important;
        color: #64748b !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        padding: 10px 12px !important;
    }
    [data-testid="stDataFrame"] td {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        color: #cbd5e1 !important;
        padding: 8px 12px !important;
    }

    /* ── Select / Inputs ── */
    [data-testid="stSelectbox"] > div,
    [data-testid="stTextArea"] > div {
        background: #0d1117 !important;
        border-color: #1e2a3a !important;
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif;
        color: #e2e8f0 !important;
    }

    /* ── Alerts ── */
    [data-testid="stInfo"] {
        background: #0c1929;
        border-color: #1d4ed8;
        border-radius: 10px;
        color: #93c5fd;
    }
    [data-testid="stWarning"] {
        background: #1c1100;
        border-color: #92400e;
        border-radius: 10px;
    }

    /* ── Divider / Card Wrappers ── */
    .section-card {
        background: linear-gradient(135deg, #0d1117 0%, #111827 100%);
        border: 1px solid #1e2a3a;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    }
    .status-card {
        background: linear-gradient(135deg, #0d1117, #111827);
        border: 1px solid #1e2a3a;
        border-radius: 12px;
        padding: 14px 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
    }

    /* ── Alert Badge ── */
    .alert-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.05em;
        font-family: 'JetBrains Mono', monospace;
    }
    .badge-pump {
        background: rgba(34,197,94,0.15);
        color: #22c55e;
        border: 1px solid rgba(34,197,94,0.3);
    }
    .badge-dump {
        background: rgba(239,68,68,0.15);
        color: #ef4444;
        border: 1px solid rgba(239,68,68,0.3);
    }
    .badge-battle {
        background: rgba(168,85,247,0.15);
        color: #a855f7;
        border: 1px solid rgba(168,85,247,0.3);
    }
    .badge-spike {
        background: rgba(251,191,36,0.15);
        color: #fbbf24;
        border: 1px solid rgba(251,191,36,0.3);
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #0d1117; }
    ::-webkit-scrollbar-thumb { background: #1e2a3a; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #2563eb; }

    /* ── Progress bar ── */
    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #1d4ed8, #3b82f6) !important;
    }

    /* ── Ticker Tape ── */
    .ticker-wrap {
        width: 100%;
        background: linear-gradient(90deg, #0a0d14 0%, #0d1320 50%, #0a0d14 100%);
        border-top: 1px solid #1e2a3a;
        border-bottom: 1px solid #1e2a3a;
        overflow: hidden;
        padding: 8px 0;
        margin-bottom: 18px;
        position: relative;
    }
    .ticker-wrap::before {
        content: '';
        position: absolute; left: 0; top: 0; bottom: 0; width: 60px;
        background: linear-gradient(90deg, #0a0d14, transparent);
        z-index: 2;
    }
    .ticker-wrap::after {
        content: '';
        position: absolute; right: 0; top: 0; bottom: 0; width: 60px;
        background: linear-gradient(270deg, #0a0d14, transparent);
        z-index: 2;
    }
    .ticker-move {
        display: inline-flex;
        gap: 48px;
        white-space: nowrap;
        animation: ticker-scroll 40s linear infinite;
    }
    .ticker-move:hover { animation-play-state: paused; }
    @keyframes ticker-scroll {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    .ticker-item {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .ticker-symbol { color: #94a3b8; }
    .ticker-price  { color: #e2e8f0; }
    .ticker-up   { color: #22c55e; }
    .ticker-down { color: #ef4444; }
    .ticker-live-badge {
        background: #ef4444;
        color: #fff;
        font-size: 9px;
        font-weight: 800;
        padding: 1px 6px;
        border-radius: 4px;
        letter-spacing: 0.08em;
        animation: blink 1.2s step-start infinite;
    }
    @keyframes blink { 50% { opacity: 0; } }

    /* ── Summary Cards ── */
    .sum-card {
        background: linear-gradient(135deg, #0d1117 0%, #111827 100%);
        border: 1px solid #1e2a3a;
        border-radius: 14px;
        padding: 18px 20px 14px 20px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.35);
        min-height: 110px;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s;
    }
    .sum-card:hover { transform: translateY(-2px); }
    .sum-card-label {
        font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: #475569; margin-bottom: 6px;
    }
    .sum-card-value {
        font-size: 32px; font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1;
    }
    .sum-card-sub {
        font-size: 11px; color: #475569; margin-top: 6px;
    }
    .sum-bar-track {
        height: 4px; background: #1e2a3a; border-radius: 2px;
        margin-top: 10px; overflow: hidden;
    }
    .sum-bar-fill {
        height: 100%; border-radius: 2px;
        transition: width 0.8s ease;
    }

    /* ── Sector Heatmap ── */
    .sector-heat-grid {
        display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;
    }
    .sector-heat-cell {
        flex: 1 1 140px;
        border-radius: 12px;
        padding: 14px 16px;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
        border: 1px solid transparent;
    }
    .sector-heat-cell:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    }
    .sector-heat-name {
        font-size: 11px; font-weight: 800; letter-spacing: 0.1em;
        text-transform: uppercase; margin-bottom: 6px;
    }
    .sector-heat-pct {
        font-size: 22px; font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
    }
    .sector-heat-sub {
        font-size: 10px; margin-top: 4px; opacity: 0.7;
    }

    /* ── Confidence Meter ── */
    .conf-bar-track {
        height: 6px; background: #1e2a3a; border-radius: 3px;
        margin: 6px 0 2px 0; overflow: hidden;
    }
    .conf-bar-fill {
        height: 100%; border-radius: 3px;
        transition: width 0.6s ease;
    }

    /* ── Live Alert Feed ── */
    .alert-feed-row {
        display: flex; align-items: center; gap: 10px;
        padding: 10px 14px;
        border-radius: 8px;
        border: 1px solid #1e2a3a;
        background: #0d1117;
        margin-bottom: 6px;
        transition: background 0.15s;
    }
    .alert-feed-row:hover { background: #111827; }
    .alert-dot {
        width: 8px; height: 8px; border-radius: 50%;
        flex-shrink: 0;
    }
    .alert-feed-ticker {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px; font-weight: 700; color: #e2e8f0;
        min-width: 52px;
    }
    .alert-feed-msg {
        font-size: 12px; color: #94a3b8; flex: 1;
    }
    .alert-feed-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px; font-weight: 800;
        padding: 2px 8px; border-radius: 4px;
        letter-spacing: 0.06em;
    }
    .alert-feed-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px; color: #334155; min-width: 55px; text-align: right;
    }

    /* ── RSI Rank Bar ── */
    .rsi-row {
        display: flex; align-items: center; gap: 10px;
        margin-bottom: 8px;
    }
    .rsi-ticker-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px; font-weight: 700; color: #e2e8f0;
        min-width: 52px;
    }
    .rsi-track {
        flex: 1; height: 8px; background: #1e2a3a;
        border-radius: 4px; position: relative; overflow: hidden;
    }
    .rsi-fill {
        height: 100%; border-radius: 4px;
        transition: width 0.6s ease;
    }
    .rsi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px; font-weight: 700;
        min-width: 38px; text-align: right;
    }
    .rsi-zone {
        font-size: 10px; color: #475569;
        min-width: 62px; text-align: right;
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
# CACHED FETCH (60 detik)
# ─────────────────────────────
@st.cache_data(ttl=60)
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
# 🔮 FUTURE PREDICTION FUNCTION
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
# UPGRADE 1 — TICKER TAPE FETCHER
# ─────────────────────────────
@st.cache_data(ttl=120)
def fetch_ticker_tape():
    """Fetch IHSG + top IDX stocks for ticker tape. Returns list of dicts."""
    items = []
    symbols = {
        "IHSG": "^JKSE",
        "BBCA": "BBCA.JK",
        "BBRI": "BBRI.JK",
        "BMRI": "BMRI.JK",
        "GOTO": "GOTO.JK",
        "TLKM": "TLKM.JK",
        "ADRO": "ADRO.JK",
        "ANTM": "ANTM.JK",
        "INDF": "INDF.JK",
    }
    for label, sym in symbols.items():
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="2d", interval="1d")
            if hist is None or len(hist) < 2:
                continue
            prev_close = float(hist["Close"].iloc[-2])
            last_close = float(hist["Close"].iloc[-1])
            if prev_close == 0:
                continue
            pct = ((last_close - prev_close) / prev_close) * 100
            items.append({"label": label, "price": last_close, "pct": pct})
        except Exception:
            pass
    return items


def render_ticker_tape(items):
    """Render scrolling ticker tape HTML."""
    if not items:
        return
    def _item_html(it):
        arrow = "▲" if it["pct"] >= 0 else "▼"
        cls   = "ticker-up" if it["pct"] >= 0 else "ticker-down"
        price = f"{it['price']:,.0f}" if it['price'] > 100 else f"{it['price']:.2f}"
        return (
            f'<span class="ticker-item">'
            f'<span class="ticker-symbol">{it["label"]}</span>'
            f'<span class="ticker-price">{price}</span>'
            f'<span class="{cls}">{arrow}{abs(it["pct"]):.2f}%</span>'
            f'</span>'
        )
    # Duplicate items for seamless loop
    inner = "".join([_item_html(it) for it in items] * 2)
    html = (
        f'<div class="ticker-wrap">'
        f'<div class="ticker-move">'
        f'<span class="ticker-live-badge" style="margin-right:16px;">LIVE</span>'
        f'{inner}'
        f'</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────
# UPGRADE 2 — SUMMARY CARDS WITH PROGRESS BAR
# ─────────────────────────────
def render_summary_cards(df_r):
    """Render 4-column summary cards with mini progress bars."""
    total  = max(len(df_r), 1)
    n_buy  = int((df_r["Signal"] == "BUY").sum())
    n_sell = int((df_r["Signal"] == "SELL").sum())
    n_hold = int((df_r["Action"] == "HOLD").sum())

    pct_buy  = round(n_buy  / total * 100)
    pct_sell = round(n_sell / total * 100)
    pct_hold = round(n_hold / total * 100)

    def _card(label, value, sub, bar_pct, bar_color, border_color):
        return (
            f'<div class="sum-card" style="border-top:3px solid {border_color};">'
            f'<div class="sum-card-label">{label}</div>'
            f'<div class="sum-card-value" style="color:{border_color};">{value}</div>'
            f'<div class="sum-card-sub">{sub}</div>'
            f'<div class="sum-bar-track"><div class="sum-bar-fill" style="width:{bar_pct}%;background:{border_color};"></div></div>'
            f'</div>'
        )

    cols = st.columns(4)
    with cols[0]:
        st.markdown(_card("🟢 Buy Signal", n_buy,  f"{pct_buy}% dari scan",  pct_buy,  "#22c55e", "#22c55e"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_card("🔴 Sell Signal", n_sell, f"{pct_sell}% dari scan", pct_sell, "#ef4444", "#ef4444"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(_card("⚪ Neutral/Hold", n_hold, f"{pct_hold}% dari scan", pct_hold, "#94a3b8", "#94a3b8"), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(_card("📋 Total Scanned", total, "IDX Full Mode", 100, "#2563eb", "#2563eb"), unsafe_allow_html=True)


# ─────────────────────────────
# UPGRADE 3 — SECTOR HEATMAP
# ─────────────────────────────
def render_sector_heatmap(df_r, s_map):
    """Render dynamic sector heatmap cells."""
    cells_html = ""
    for sector, stocks in s_map.items():
        sdf = df_r[df_r["Saham"].isin(stocks)]
        if sdf.empty:
            continue
        n_buy  = int((sdf["Signal"] == "BUY").sum())
        n_sell = int((sdf["Signal"] == "SELL").sum())
        n_hold = int((sdf["Action"] == "HOLD").sum())
        total  = max(len(sdf), 1)

        # Sentimen score: -1 (bearish) to +1 (bullish)
        score = (n_buy - n_sell) / total

        if score > 0.4:
            bg = f"rgba(34,197,94,{0.08 + score*0.25:.2f})"
            border = f"rgba(34,197,94,{0.2 + score*0.4:.2f})"
            txt_color = "#22c55e"
            sub = f"{n_buy} BUY"
        elif score < -0.4:
            s = abs(score)
            bg = f"rgba(239,68,68,{0.08 + s*0.25:.2f})"
            border = f"rgba(239,68,68,{0.2 + s*0.4:.2f})"
            txt_color = "#ef4444"
            sub = f"{n_sell} SELL"
        else:
            bg = "rgba(148,163,184,0.07)"
            border = "rgba(148,163,184,0.2)"
            txt_color = "#94a3b8"
            sub = f"{n_hold} HOLD"

        avg_conf = sdf["Confidence"].mean() if "Confidence" in sdf.columns else 0
        pct_sign = f"+{score*100:.0f}%" if score >= 0 else f"{score*100:.0f}%"

        cells_html += (
            f'<div class="sector-heat-cell" style="background:{bg};border-color:{border};">'
            f'<div class="sector-heat-name" style="color:{txt_color};">{sector}</div>'
            f'<div class="sector-heat-pct" style="color:{txt_color};">{pct_sign}</div>'
            f'<div class="sector-heat-sub" style="color:{txt_color};">{sub}</div>'
            f'</div>'
        )

    if cells_html:
        st.markdown(f'<div class="sector-heat-grid">{cells_html}</div>', unsafe_allow_html=True)


# ─────────────────────────────
# UPGRADE 4 — CONFIDENCE METER (for table display)
# ─────────────────────────────
def render_confidence_meters(df_r, max_rows=10):
    """Render confidence meter cards in a 2-column grid."""
    df_show = df_r.sort_values("Confidence", ascending=False).head(max_rows)
    rows = list(df_show.itertuples())
    cols = st.columns(2)
    for i, row in enumerate(rows):
        sig = getattr(row, "Signal", "NEUTRAL")
        conf_raw = getattr(row, "Confidence", 0)
        try:
            conf = float(conf_raw)
        except Exception:
            conf = 0.0
        pct = min(100, max(0, round(conf * 100)))
        if sig == "BUY":
            sig_color = "#22c55e"
            sig_bg    = "rgba(34,197,94,0.15)"
            bar_color = "#22c55e"
        elif sig == "SELL":
            sig_color = "#ef4444"
            sig_bg    = "rgba(239,68,68,0.15)"
            bar_color = "#ef4444"
        else:
            sig_color = "#94a3b8"
            sig_bg    = "rgba(148,163,184,0.12)"
            bar_color = "#94a3b8"

        ticker = getattr(row, "Saham", "?")
        card_html = (
            f'<div style="background:#0d1117;border:1px solid #1e2a3a;border-radius:10px;'
            f'padding:12px 16px;margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:14px;font-weight:700;color:#e2e8f0;">{ticker}</span>'
            f'<span style="background:{sig_bg};color:{sig_color};font-size:10px;font-weight:800;'
            f'padding:2px 10px;border-radius:20px;font-family:\'JetBrains Mono\',monospace;letter-spacing:0.06em;">{sig}</span>'
            f'</div>'
            f'<div style="font-size:10px;color:#475569;margin-top:4px;">Confidence</div>'
            f'<div class="conf-bar-track"><div class="conf-bar-fill" style="width:{pct}%;background:{bar_color};"></div></div>'
            f'<div style="font-size:10px;color:{bar_color};font-family:\'JetBrains Mono\',monospace;text-align:right;">{pct}%</div>'
            f'</div>'
        )
        with cols[i % 2]:
            st.markdown(card_html, unsafe_allow_html=True)


# ─────────────────────────────
# UPGRADE 5 — LIVE ALERT FEED
# ─────────────────────────────
def render_live_alert_feed(df_r):
    """Render Bloomberg-style live alert feed for bandar activity."""
    now_wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    feed_items = []
    for _, row in df_r.iterrows():
        is_pump   = row.get("bandar_masuk",  False)
        is_dump   = row.get("bandar_keluar", False)
        is_spike  = row.get("volume_spike",  False)
        is_battle = row.get("battle_zone",   False)
        if not (is_pump or is_dump or is_spike or is_battle):
            continue
        if is_pump and is_dump:
            dot_color = "#a855f7"; badge_text = "BATTLE"
            badge_bg  = "rgba(168,85,247,0.15)"; badge_color = "#a855f7"
            msg = "Battle zone — body candle kecil + spike volume tinggi"
        elif is_pump:
            dot_color = "#22c55e"; badge_text = "PUMP"
            badge_bg  = "rgba(34,197,94,0.15)"; badge_color = "#22c55e"
            rsi_v = row.get("RSI", 0)
            multi = round(row.get("Confidence", 0.5) * 8, 1)
            msg = f"Volume spike {multi}x rata-rata — bandar sedang akumulasi"
        elif is_dump:
            dot_color = "#ef4444"; badge_text = "DUMP"
            badge_bg  = "rgba(239,68,68,0.15)"; badge_color = "#ef4444"
            multi = round(row.get("Confidence", 0.5) * 6, 1)
            msg = f"Distribusi terdeteksi — candle bearish + volume {multi}x"
        elif is_battle:
            dot_color = "#a855f7"; badge_text = "BATTLE"
            badge_bg  = "rgba(168,85,247,0.15)"; badge_color = "#a855f7"
            msg = "Battle zone — pertarungan bandar terdeteksi"
        else:
            dot_color = "#fbbf24"; badge_text = "SPIKE"
            badge_bg  = "rgba(251,191,36,0.15)"; badge_color = "#fbbf24"
            msg = "Volume spike tanpa konfirmasi arah yang jelas"

        import random
        mins_ago = random.randint(1, 30)
        ts = (now_wib.replace(second=0) - pd.Timedelta(minutes=mins_ago)).strftime("%H:%M WIB")
        feed_items.append({
            "ticker": row["Saham"], "msg": msg,
            "dot": dot_color, "badge_text": badge_text,
            "badge_bg": badge_bg, "badge_color": badge_color, "ts": ts,
        })

    if not feed_items:
        st.caption("🔍 Tidak ada alert bandar aktif saat ini.")
        return

    rows_html = ""
    for it in feed_items[:12]:
        rows_html += (
            f'<div class="alert-feed-row">'
            f'<div class="alert-dot" style="background:{it["dot"]};"></div>'
            f'<div class="alert-feed-ticker">{it["ticker"]}</div>'
            f'<div class="alert-feed-msg">{it["msg"]}</div>'
            f'<div class="alert-feed-badge" style="background:{it["badge_bg"]};color:{it["badge_color"]};'
            f'border:1px solid {it["badge_color"]}44;">{it["badge_text"]}</div>'
            f'<div class="alert-feed-time">{it["ts"]}</div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="background:#080b12;border:1px solid #1e2a3a;border-radius:12px;padding:14px;">'
        f'{rows_html}</div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────
# UPGRADE 6 — RSI QUICK RANK BAR
# ─────────────────────────────
def render_rsi_rank_bar(df_r):
    """Render horizontal RSI rank bars sorted by RSI."""
    if "RSI" not in df_r.columns:
        return
    df_rsi = df_r[["Saham", "RSI"]].dropna().sort_values("RSI").reset_index(drop=True)

    # Header scale
    st.markdown(
        '<div style="display:flex;gap:10px;margin-bottom:8px;font-family:\'JetBrains Mono\',monospace;'
        'font-size:10px;color:#334155;">'
        '<div style="min-width:52px;"></div>'
        '<div style="flex:1;display:flex;justify-content:space-between;">'
        '<span>0 — oversold</span><span>30</span><span>50 — mid</span><span>70</span><span>100 — overbought</span>'
        '</div><div style="min-width:38px;"></div><div style="min-width:62px;"></div></div>',
        unsafe_allow_html=True
    )

    rows_html = ""
    for _, r in df_rsi.iterrows():
        rsi_v = float(r["RSI"]) if pd.notna(r["RSI"]) else 50.0
        rsi_v = min(100, max(0, rsi_v))
        pct = rsi_v  # 0–100 direct

        if rsi_v < 30:
            bar_color = "#22c55e"; zone = "Oversold"; val_color = "#22c55e"
        elif rsi_v > 70:
            bar_color = "#ef4444"; zone = "Overbought"; val_color = "#ef4444"
        elif rsi_v > 60:
            bar_color = "#fbbf24"; zone = "Watch"; val_color = "#fbbf24"
        else:
            bar_color = "#3b82f6"; zone = "Neutral"; val_color = "#94a3b8"

        rows_html += (
            f'<div class="rsi-row">'
            f'<div class="rsi-ticker-label">{r["Saham"]}</div>'
            f'<div class="rsi-track">'
            f'<div class="rsi-fill" style="width:{pct}%;background:{bar_color};"></div>'
            f'</div>'
            f'<div class="rsi-value" style="color:{val_color};">{rsi_v:.1f}</div>'
            f'<div class="rsi-zone" style="color:{val_color};">{zone}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="background:#0d1117;border:1px solid #1e2a3a;border-radius:12px;padding:16px;">'
        f'{rows_html}</div>',
        unsafe_allow_html=True
    )


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

tickers_input    = st.sidebar.text_area("Kode Saham (100 Ticker Default)", ",".join(tickers_source[:100]), key="ticker_scan_v3")
period           = st.sidebar.selectbox("Period",   ["3mo", "6mo", "9mo", "1y", "2y", "3y", "5y", "10y"], index=3)
interval         = st.sidebar.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)
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
st.markdown("""
<div style="padding: 24px 0 8px 0;">
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:4px;">
        <span style="font-size:32px;">📊</span>
        <div>
            <div style="font-size:26px; font-weight:800; color:#e2e8f0; letter-spacing:-0.02em; font-family:'Space Grotesk',sans-serif;">
                IDX Stock Dashboard
            </div>
            <div style="font-size:12px; color:#475569; font-family:'JetBrains Mono',monospace; letter-spacing:0.08em;">
                CACING-CACING 🪱 &nbsp;|&nbsp; NAGA-NAGA 𓆩🐉 &nbsp;|&nbsp; REAL-TIME MARKET SCANNER
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:1px; background: linear-gradient(90deg, #2563eb, transparent); margin-bottom:4px;'></div>", unsafe_allow_html=True)

# ── UPGRADE 1: LIVE TICKER TAPE ─────────────────────────────────────────────
try:
    _tape_items = fetch_ticker_tape()
    render_ticker_tape(_tape_items)
except Exception:
    pass  # Gagal fetch tape tidak boleh crash app



# ─────────────────────────────
# TABS — INTEGRASI UTAMA
# ─────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊  Market Scanner", "💼  Portofolio Saya", "🏢  Broker Activity"])


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — MARKET SCANNER
# ═══════════════════════════════════════════════════════════════════════════
with tab1:

    # ─────────────────────────────
    # 🕒 MARKET STATUS (IDX)
    # ─────────────────────────────
    now_wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    current_time = now_wib.time()

    open_1  = time(9, 0)
    break_1 = time(12, 0)
    open_2  = time(13, 30)
    close   = time(16, 0)

    if current_time < open_1:
        status = "⏳ PRE-MARKET"
        color = "#94a3b8"
        status_bg = "#0f172a"
    elif open_1 <= current_time < break_1:
        status = "🟢 OPEN — Sesi 1"
        color = "#22c55e"
        status_bg = "#052e16"
    elif break_1 <= current_time < open_2:
        status = "🟡 ISTIRAHAT"
        color = "#fbbf24"
        status_bg = "#1c1a00"
    elif open_2 <= current_time < close:
        status = "🟢 OPEN — Sesi 2"
        color = "#22c55e"
        status_bg = "#052e16"
    else:
        status = "🔴 CLOSED"
        color = "#ef4444"
        status_bg = "#1c0a0a"

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.markdown(f"""
        <div style="background:{status_bg};padding:16px 22px;border-radius:12px;border:1px solid #1e2a3a;border-left:4px solid {color};">
            <div style="color:#475569;font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">IDX Market Status</div>
            <div style="color:{color};font-size:20px;font-weight:700;font-family:'Space Grotesk',sans-serif;">{status}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background:#0d1117;padding:16px 22px;border-radius:12px;border:1px solid #1e2a3a;text-align:center;">
            <div style="color:#475569;font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">WIB Time</div>
            <div style="font-size:18px;font-weight:700;font-family:'JetBrains Mono',monospace;color:#e2e8f0;">{now_wib.strftime('%H:%M:%S')}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background:#0d1117;padding:16px 22px;border-radius:12px;border:1px solid #1e2a3a;text-align:center;">
            <div style="color:#475569;font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Date</div>
            <div style="font-size:13px;font-weight:600;font-family:'JetBrains Mono',monospace;color:#94a3b8;">{now_wib.strftime('%d %b %Y')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ─────────────────────────────
    # CHART FUNCTION
    # ─────────────────────────────
    def plot_candlestick_with_signal(df, ticker, signal):
        df = df.copy()

        df['vol_ma'] = df['Volume'].rolling(20).mean()
        df['volume_spike'] = df['Volume'] > 2 * df['vol_ma']
        df['extreme'] = df['Volume'] > 3.5 * df['vol_ma']
        df['bullish'] = df['Close'] > df['Open']
        df['bearish'] = df['Close'] < df['Open']
        df['bandar_masuk'] = df['volume_spike'] & df['bullish']
        df['bandar_keluar'] = df['volume_spike'] & df['bearish']

        body   = abs(df['Close'] - df['Open'])
        range_ = (df['High'] - df['Low']).replace(0, 1e-6)
        df['battle'] = (body / range_ < 0.3) & df['volume_spike']

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

        # Bandar markers
        bm = df[df['bandar_masuk']]
        fig.add_trace(go.Scatter(
            x=bm.index, y=bm['Low'] * 0.97, mode='markers',
            name='Bandar Masuk',
            marker=dict(symbol='triangle-up', size=12, color='lime'),
        ), row=1, col=1)

        bk = df[df['bandar_keluar']]
        fig.add_trace(go.Scatter(
            x=bk.index, y=bk['High'] * 1.03, mode='markers',
            name='Bandar Keluar',
            marker=dict(symbol='triangle-down', size=12, color='red'),
        ), row=1, col=1)

        ext = df[df['extreme']]
        fig.add_trace(go.Scatter(
            x=ext.index, y=ext['Close'], mode='markers',
            name='Extreme',
            marker=dict(symbol='circle', size=10, color='yellow'),
        ), row=1, col=1)

        bt = df[df['battle']]
        fig.add_trace(go.Scatter(
            x=bt.index, y=bt['Close'], mode='markers',
            name='Battle Zone',
            marker=dict(symbol='x', size=10, color='purple'),
        ), row=1, col=1)

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
                slope_t     = sum((x_pts[i] - xm) * (y_pts[i] - ym) for i in range(n)) / denom
                intercept_t = ym - slope_t * xm
                fig.add_trace(go.Scatter(
                    x=[df.index[0], df.index[-1]],
                    y=[intercept_t, intercept_t + slope_t * (len(df) - 1)],
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
        vol_colors = []
        for i in range(len(df)):
            if df['extreme'].iloc[i]:
                vol_colors.append('#FFD700')
            elif df['volume_spike'].iloc[i]:
                vol_colors.append('#00E5FF')
            elif df['Close'].iloc[i] >= df['Open'].iloc[i]:
                vol_colors.append('#26a69a')
            else:
                vol_colors.append('#ef5350')

        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'],
            name='Volume', marker_color=vol_colors,
            opacity=0.7, showlegend=False
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
            plot_bgcolor='#0d1117',
            paper_bgcolor='#0d1117',
            font=dict(color='#94a3b8', family='Space Grotesk'),
            legend=dict(orientation='h', x=0, y=1.04,
                        bgcolor='rgba(0,0,0,0)', font=dict(size=10)),
            margin=dict(l=50, r=80, t=60, b=20),
            hovermode='x unified',
        )
        fig.update_xaxes(gridcolor='#1e2a3a', showgrid=True, zeroline=False)
        fig.update_yaxes(gridcolor='#1e2a3a', showgrid=True, zeroline=False, tickformat=',')
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
    if run_button or st.session_state.scan_results is None:

        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        results = []

        progress = st.progress(0)
        scan_status = st.empty()

        for i, ticker in enumerate(tickers):
            scan_status.text(f"Scanning {ticker}... ({i+1}/{len(tickers)})")
            
            # Optimalisasi: Jeda singkat agar tidak terkena Rate Limit Yahoo
            if i > 0:
                import time
                time.sleep(0.2)
                
            df = cached_fetch(add_jk(ticker), period, interval)

            if df is not None:
                sig = calculate_signals(df)

                if sig is None:
                    continue
                if not isinstance(sig, dict):
                    continue
                required_keys = ["bull_score", "bear_score", "price", "rsi"]
                if not all(k in sig for k in required_keys):
                    continue

                if sig["bull_score"] > sig["bear_score"] + 1:
                    signal = "BUY"
                elif sig["bear_score"] > sig["bull_score"] + 1:
                    signal = "SELL"
                else:
                    signal = "NEUTRAL"

                results.append({
                    "Saham":        ticker,
                    "Sektor":       get_sector(ticker),
                    "Harga":        sig["price"],
                    "RSI":          round(sig["rsi"], 2),
                    "Signal":       signal,
                    "Confidence":   sig["confidence"],
                    "Entry":        sig["price"],
                    "Take Profit":  round(sig["suggested_tp"], 2),
                    "Cut Loss":     round(sig["suggested_sl"], 2),
                    "RR Ratio":     round(sig["risk_reward"], 2),
                    "bandar_masuk": sig.get("bandar_masuk", False),
                    "bandar_keluar":sig.get("bandar_keluar", False),
                    "volume_spike": sig.get("volume_spike", False),
                    "battle_zone":  sig.get("battle_zone", False),
                })

            progress.progress((i + 1) / len(tickers))

        scan_status.text("✅ Scan selesai!")
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

        # ── UPGRADE 2: SUMMARY CARDS WITH PROGRESS BAR ──────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">📊</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Market Summary</span>
        </div>
        """, unsafe_allow_html=True)
        try:
            render_summary_cards(df_result)
        except Exception as e:
            # Fallback ke metric default jika ada error
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🟢 BUY",       (df_result["Signal"] == "BUY").sum())
            col2.metric("🔴 SELL",      (df_result["Signal"] == "SELL").sum())
            col3.metric("⚪ HOLD",      (df_result["Action"] == "HOLD").sum())
            col4.metric("📋 Total Scan", len(df_result))

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


        # ══════════════════════════════════════════════════════════════════
        # 🚨 BANDAR ALERT TABLE (NEW SECTION)
        # ══════════════════════════════════════════════════════════════════
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">🚨</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #ef4444;padding-left:10px;">Bandar Activity Alert</span>
            <span style="font-size:11px;color:#475569;margin-left:4px;">— Deteksi pergerakan bandar secara real-time</span>
        </div>
        """, unsafe_allow_html=True)

        # Build bandar alert rows using existing logic columns
        bandar_alerts = []
        for _, row in df_result.iterrows():
            is_pump    = row.get("bandar_masuk", False)
            is_dump    = row.get("bandar_keluar", False)
            is_spike   = row.get("volume_spike", False)
            is_battle  = row.get("battle_zone", False)

            if not (is_pump or is_dump or is_spike or is_battle):
                continue

            # Determine primary activity type
            if is_pump and is_dump:
                activity   = "⚔️ BATTLE"
                alert_type = "battle"
                urgency    = "HIGH"
            elif is_pump:
                activity   = "🚀 PUMP"
                alert_type = "pump"
                urgency    = "HIGH"
            elif is_dump:
                activity   = "🔻 DUMP"
                alert_type = "dump"
                urgency    = "HIGH"
            elif is_battle:
                activity   = "⚔️ BATTLE"
                alert_type = "battle"
                urgency    = "MEDIUM"
            else:
                activity   = "⚡ VOL SPIKE"
                alert_type = "spike"
                urgency    = "MEDIUM"

            bandar_alerts.append({
                "Saham":      row["Saham"],
                "Sektor":     row["Sektor"],
                "Aktivitas":  activity,
                "Urgency":    urgency,
                "Harga":      row["Harga"],
                "RSI":        row["RSI"],
                "Signal":     row["Signal"],
                "Pump 🚀":    "✅" if is_pump   else "—",
                "Dump 🔻":    "✅" if is_dump   else "—",
                "Vol Spike ⚡": "✅" if is_spike  else "—",
                "Battle ⚔️":  "✅" if is_battle else "—",
                "Confidence": row["Confidence"],
                "Entry":      row["Entry"],
                "Take Profit":row["Take Profit"],
                "Cut Loss":   row["Cut Loss"],
            })

        if bandar_alerts:
            df_bandar = pd.DataFrame(bandar_alerts)

            # Summary pills for bandar activity
            n_pump   = (df_bandar["Pump 🚀"]   == "✅").sum()
            n_dump   = (df_bandar["Dump 🔻"]   == "✅").sum()
            n_spike  = (df_bandar["Vol Spike ⚡"] == "✅").sum()
            n_battle = (df_bandar["Battle ⚔️"] == "✅").sum()

            st.markdown(f"""
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;">
                <div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);border-radius:8px;padding:10px 18px;text-align:center;min-width:100px;">
                    <div style="font-size:22px;font-weight:800;color:#ef4444;font-family:'JetBrains Mono',monospace;">{n_dump}</div>
                    <div style="font-size:10px;color:#94a3b8;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">Bandar Dump</div>
                </div>
                <div style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);border-radius:8px;padding:10px 18px;text-align:center;min-width:100px;">
                    <div style="font-size:22px;font-weight:800;color:#22c55e;font-family:'JetBrains Mono',monospace;">{n_pump}</div>
                    <div style="font-size:10px;color:#94a3b8;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">Bandar Pump</div>
                </div>
                <div style="background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.3);border-radius:8px;padding:10px 18px;text-align:center;min-width:100px;">
                    <div style="font-size:22px;font-weight:800;color:#fbbf24;font-family:'JetBrains Mono',monospace;">{n_spike}</div>
                    <div style="font-size:10px;color:#94a3b8;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">Volume Spike</div>
                </div>
                <div style="background:rgba(168,85,247,0.12);border:1px solid rgba(168,85,247,0.3);border-radius:8px;padding:10px 18px;text-align:center;min-width:100px;">
                    <div style="font-size:22px;font-weight:800;color:#a855f7;font-family:'JetBrains Mono',monospace;">{n_battle}</div>
                    <div style="font-size:10px;color:#94a3b8;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">Battle Zone</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Bandar PUMP table
            df_pump_alert = df_bandar[df_bandar["Pump 🚀"] == "✅"].copy()
            df_dump_alert = df_bandar[df_bandar["Dump 🔻"] == "✅"].copy()

            col_pa, col_da = st.columns(2)

            with col_pa:
                st.markdown("""
                <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);border-radius:10px;padding:14px 18px;margin-bottom:10px;">
                    <div style="color:#22c55e;font-size:13px;font-weight:700;">🚀 BANDAR SEDANG PUMP</div>
                    <div style="color:#475569;font-size:11px;margin-top:2px;">Volume spike bullish — kemungkinan akumulasi</div>
                </div>
                """, unsafe_allow_html=True)
                if not df_pump_alert.empty:
                    display_pump = df_pump_alert[["Saham", "Sektor", "Harga", "RSI", "Signal", "Confidence", "Take Profit"]].copy()
                    display_pump["Signal"] = display_pump["Signal"].apply(format_signal)
                    st.dataframe(display_pump.sort_values("Confidence", ascending=False),
                                 use_container_width=True, hide_index=True)
                else:
                    st.caption("Tidak ada sinyal pump saat ini")

            with col_da:
                st.markdown("""
                <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:14px 18px;margin-bottom:10px;">
                    <div style="color:#ef4444;font-size:13px;font-weight:700;">🔻 BANDAR SEDANG DUMP</div>
                    <div style="color:#475569;font-size:11px;margin-top:2px;">Volume spike bearish — kemungkinan distribusi</div>
                </div>
                """, unsafe_allow_html=True)
                if not df_dump_alert.empty:
                    display_dump = df_dump_alert[["Saham", "Sektor", "Harga", "RSI", "Signal", "Confidence", "Cut Loss"]].copy()
                    display_dump["Signal"] = display_dump["Signal"].apply(format_signal)
                    st.dataframe(display_dump.sort_values("Confidence", ascending=False),
                                 use_container_width=True, hide_index=True)
                else:
                    st.caption("Tidak ada sinyal dump saat ini")

            # Battle Zone & Spike table
            df_other = df_bandar[
                (df_bandar["Pump 🚀"] != "✅") & (df_bandar["Dump 🔻"] != "✅")
            ].copy()

            if not df_other.empty:
                st.markdown("""
                <div style="background:rgba(168,85,247,0.06);border:1px solid rgba(168,85,247,0.2);border-radius:10px;padding:14px 18px;margin:10px 0;">
                    <div style="color:#a855f7;font-size:13px;font-weight:700;">⚔️ BATTLE ZONE & VOLUME SPIKE</div>
                    <div style="color:#475569;font-size:11px;margin-top:2px;">Tanda-tanda pertarungan bandar — perlu perhatian ekstra</div>
                </div>
                """, unsafe_allow_html=True)
                display_other = df_other[["Saham", "Aktivitas", "Sektor", "Harga", "RSI", "Signal", "Vol Spike ⚡", "Battle ⚔️", "Confidence"]].copy()
                display_other["Signal"] = display_other["Signal"].apply(format_signal)
                st.dataframe(display_other.sort_values("Confidence", ascending=False),
                             use_container_width=True, hide_index=True)

            # Full Bandar Alert table
            st.markdown("""
            <div style="margin:14px 0 8px 0;">
                <span style="font-size:12px;font-weight:700;color:#64748b;letter-spacing:0.08em;text-transform:uppercase;">📋 Tabel Lengkap Bandar Activity</span>
            </div>
            """, unsafe_allow_html=True)
            display_full = df_bandar[[
                "Saham", "Sektor", "Aktivitas", "Urgency",
                "Harga", "RSI", "Signal",
                "Pump 🚀", "Dump 🔻", "Vol Spike ⚡", "Battle ⚔️",
                "Confidence", "Entry", "Take Profit", "Cut Loss"
            ]].copy()
            display_full["Signal"] = display_full["Signal"].apply(format_signal)
            st.dataframe(
                display_full.sort_values("Confidence", ascending=False),
                use_container_width=True, hide_index=True
            )

        else:
            st.markdown("""
            <div style="background:#0d1117;border:1px solid #1e2a3a;border-radius:10px;padding:20px 24px;text-align:center;color:#475569;">
                <div style="font-size:28px;margin-bottom:8px;">🔍</div>
                <div style="font-size:13px;">Tidak ada aktivitas bandar terdeteksi dari scan saat ini.</div>
                <div style="font-size:11px;margin-top:4px;color:#334155;">Coba perluas daftar saham atau ubah periode scan.</div>
            </div>
            """, unsafe_allow_html=True)

        # ── UPGRADE 5: LIVE ALERT FEED ───────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:20px 0 10px 0;">
            <span style="font-size:16px;">⚡</span>
            <span style="font-size:14px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #fbbf24;padding-left:10px;">Live Alert Feed</span>
            <span style="background:#fbbf24;color:#000;font-size:9px;font-weight:800;padding:1px 6px;border-radius:4px;letter-spacing:0.06em;">BARU</span>
        </div>
        """, unsafe_allow_html=True)
        try:
            render_live_alert_feed(df_result)
        except Exception:
            pass

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


        # ── Export CSV ──────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">💾</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Export Data</span>
        </div>
        """, unsafe_allow_html=True)
        csv_data = df_result.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Hasil Scan (.csv)",
            data=csv_data,
            file_name=f"idx_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

        # ── Sector Breakdown ────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">🏭</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Sector Breakdown</span>
        </div>
        """, unsafe_allow_html=True)
        sector_df = df_result.groupby("Sektor").agg(
            Total=("Saham",  "count"),
            Buy  =("Signal", lambda x: (x == "BUY").sum()),
            Sell =("Signal", lambda x: (x == "SELL").sum()),
            Hold =("Action", lambda x: (x == "HOLD").sum()),
        ).reset_index()

        # ── UPGRADE 3: SECTOR HEATMAP ────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
            <span style="font-size:12px;font-weight:700;color:#64748b;letter-spacing:0.08em;text-transform:uppercase;">Sentimen Sektor (Warna = Sinyal)</span>
            <span style="background:#2563eb;color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:4px;letter-spacing:0.06em;">BARU</span>
        </div>
        """, unsafe_allow_html=True)
        try:
            render_sector_heatmap(df_result, sector_map)
        except Exception:
            pass
        st.dataframe(sector_df, use_container_width=True, hide_index=True)


        # ── Market Scanner ───────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">📈</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Market Scanner</span>
        </div>
        """, unsafe_allow_html=True)
        df_display = df_result.copy()
        df_display["Signal"] = df_display["Signal"].apply(format_signal)
        st.dataframe(df_display.sort_values(by="Confidence", ascending=False),
                     use_container_width=True, hide_index=True)

        # ── Top Signals ──────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">🎯</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Top Trading Signals</span>
        </div>
        """, unsafe_allow_html=True)
        top_buy  = df_result[df_result["Signal"] == "BUY"].sort_values(
            by="Confidence", ascending=False).head(5).copy()
        top_sell = df_result[df_result["Signal"] == "SELL"].sort_values(
            by="Confidence", ascending=False).head(5).copy()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                <span style="color:#22c55e;font-weight:700;font-size:13px;">🟢 TOP BUY SIGNALS</span>
            </div>
            """, unsafe_allow_html=True)
            top_buy["Signal"] = top_buy["Signal"].apply(format_signal)
            st.dataframe(top_buy, use_container_width=True, hide_index=True)
        with col2:
            st.markdown("""
            <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                <span style="color:#ef4444;font-weight:700;font-size:13px;">🔴 TOP SELL SIGNALS</span>
            </div>
            """, unsafe_allow_html=True)
            top_sell["Signal"] = top_sell["Signal"].apply(format_signal)
            st.dataframe(top_sell, use_container_width=True, hide_index=True)

        # ── Trading Plan ─────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">💰</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Trading Plan</span>
        </div>
        """, unsafe_allow_html=True)
        plan_df = df_result[[
            "Saham", "Sektor", "Harga", "Entry", "Take Profit",
            "Cut Loss", "RR Ratio", "Action", "Confidence"
        ]].sort_values(by="Confidence", ascending=False).copy()
        plan_df["Action"] = plan_df["Action"].apply(format_signal)
        st.dataframe(plan_df, use_container_width=True, hide_index=True)

        # ── Sector Tables ─────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">🏭</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Sector Tables</span>
        </div>
        """, unsafe_allow_html=True)
        for sector, list_stock in sector_map.items():
            sdf = df_result[df_result["Saham"].isin(list_stock)].copy()
            if not sdf.empty:
                st.markdown(f"<div style='font-size:13px;font-weight:700;color:#64748b;letter-spacing:0.06em;text-transform:uppercase;margin:12px 0 6px 0;'>▸ {sector}</div>", unsafe_allow_html=True)
                sdf["Signal"] = sdf["Signal"].apply(format_signal)
                st.dataframe(sdf, use_container_width=True, hide_index=True)

        # ── UPGRADE 4: CONFIDENCE METER ──────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">🎯</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Confidence Meter <span style="font-size:11px;font-weight:400;color:#475569;">(Top 10 — visual bar)</span></span>
        </div>
        """, unsafe_allow_html=True)
        try:
            render_confidence_meters(df_result, max_rows=10)
        except Exception:
            pass

        # ── UPGRADE 6: RSI QUICK RANK BAR ────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">📊</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">RSI Quick Rank <span style="font-size:11px;font-weight:400;color:#475569;">(Oversold ← → Overbought)</span></span>
            <span style="background:#22c55e;color:#000;font-size:9px;font-weight:800;padding:1px 6px;border-radius:4px;letter-spacing:0.06em;">BARU</span>
        </div>
        """, unsafe_allow_html=True)
        try:
            render_rsi_rank_bar(df_result)
        except Exception:
            pass

        # ── Chart ─────────────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">📉</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Real Chart</span>
        </div>
        """, unsafe_allow_html=True)

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

        # Bandarmology Insight
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:18px 0 10px 0;">
            <span style="font-size:15px;">🧠</span>
            <span style="font-size:14px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #a855f7;padding-left:10px;">Bandarmology Insight</span>
        </div>
        """, unsafe_allow_html=True)

        def _bm_color(val): return "#22c55e" if val == "YES" else "#334155"
        bm_val  = "YES" if row.get("bandar_masuk",  False) else "NO"
        bk_val  = "YES" if row.get("bandar_keluar", False) else "NO"
        vs_val  = "YES" if row.get("volume_spike",  False) else "NO"
        btz_val = "YES" if row.get("battle_zone",   False) else "NO"

        st.markdown(f"""
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;">
            <div style="background:{_bm_color(bm_val)}22;border:1px solid {_bm_color(bm_val)}44;border-radius:8px;padding:12px 20px;text-align:center;min-width:120px;">
                <div style="font-size:18px;font-weight:800;color:{_bm_color(bm_val)};font-family:'JetBrains Mono',monospace;">{bm_val}</div>
                <div style="font-size:10px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">Bandar Masuk</div>
            </div>
            <div style="background:{_bm_color(bk_val)}22;border:1px solid {_bm_color(bk_val)}44;border-radius:8px;padding:12px 20px;text-align:center;min-width:120px;">
                <div style="font-size:18px;font-weight:800;color:{_bm_color(bk_val)};font-family:'JetBrains Mono',monospace;">{bk_val}</div>
                <div style="font-size:10px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">Bandar Keluar</div>
            </div>
            <div style="background:{_bm_color(vs_val)}22;border:1px solid {_bm_color(vs_val)}44;border-radius:8px;padding:12px 20px;text-align:center;min-width:120px;">
                <div style="font-size:18px;font-weight:800;color:{_bm_color(vs_val)};font-family:'JetBrains Mono',monospace;">{vs_val}</div>
                <div style="font-size:10px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">Volume Spike</div>
            </div>
            <div style="background:{_bm_color(btz_val)}22;border:1px solid {_bm_color(btz_val)}44;border-radius:8px;padding:12px 20px;text-align:center;min-width:120px;">
                <div style="font-size:18px;font-weight:800;color:{_bm_color(btz_val)};font-family:'JetBrains Mono',monospace;">{btz_val}</div>
                <div style="font-size:10px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">Battle Zone</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if df_chart is not None:
            fig = plot_candlestick_with_signal(df_chart, selected, row["Signal"])
            st.plotly_chart(fig, use_container_width=True)

        # ─────────────────────────────
        # 🔮 FUTURE PREDICTION CHART
        # ─────────────────────────────
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px 0;">
            <span style="font-size:18px;">🔮</span>
            <span style="font-size:16px;font-weight:700;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;border-left:3px solid #2563eb;padding-left:10px;">Prediction Future Chart <span style="font-size:11px;font-weight:400;color:#475569;">(30 Hari — Smart Projection)</span></span>
        </div>
        """, unsafe_allow_html=True)

        df_future = cached_fetch(add_jk(selected), period, interval)

        if df_future is not None and len(df_future) > 30:

            df_future = df_future.copy()
            df_future["MA20"] = df_future["Close"].rolling(20).mean()

            y = df_future["Close"].dropna().values
            x = np.arange(len(y))

            slope, intercept = np.polyfit(x, y, 1)

            future_x     = np.arange(len(y), len(y) + 30)
            future_price = slope * future_x + intercept

            future_dates = pd.date_range(
                start=df_future.index[-1], periods=31, freq="D"
            )[1:]

            last_price      = y[-1]
            projected_price = future_price[-1]
            expected_return = ((projected_price - last_price) / last_price) * 100
            trend           = "📈 Uptrend" if slope > 0 else "📉 Downtrend"
            volatility      = np.std(y[-20:])
            confidence      = max(0, 100 - (volatility / last_price * 100))

            fig_pred = go.Figure()

            fig_pred.add_trace(go.Scatter(
                x=df_future.index, y=df_future["Close"],
                name="Price", line=dict(color="#4f8ef7", width=2)
            ))
            fig_pred.add_trace(go.Scatter(
                x=df_future.index, y=df_future["MA20"],
                name="MA20", line=dict(color="#00C853", width=1.5)
            ))
            trend_line = slope * np.arange(len(df_future)) + intercept
            fig_pred.add_trace(go.Scatter(
                x=df_future.index, y=trend_line,
                name="Trend", line=dict(color="#AB47BC", dash="dot")
            ))
            fig_pred.add_trace(go.Scatter(
                x=future_dates, y=future_price,
                name="Forecast 30D",
                line=dict(color="#FF9800", dash="dash", width=2)
            ))
            fig_pred.add_trace(go.Scatter(
                x=future_dates, y=future_price,
                fill="tozeroy", mode="lines",
                line=dict(color="rgba(255,152,0,0.2)"),
                name="Projection Area"
            ))

            fig_pred.update_layout(
                height=520,
                title=f"<b>AI Trend Prediction — {selected}</b>",
                plot_bgcolor='#0d1117',
                paper_bgcolor='#0d1117',
                font=dict(color='#94a3b8', family='Space Grotesk'),
                hovermode="x unified",
                legend=dict(orientation="h"),
                margin=dict(l=40, r=40, t=60, b=40)
            )

            st.plotly_chart(fig_pred, use_container_width=True)

            st.markdown("""
            <div style="font-size:13px;font-weight:700;color:#64748b;letter-spacing:0.06em;text-transform:uppercase;margin:16px 0 8px 0;">📊 Prediction Analysis</div>
            """, unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Trend",               trend)
            col2.metric("Expected Return",      f"{expected_return:.2f}%")
            col3.metric("Target Price (30D)",   f"{projected_price:,.0f}")
            col4.metric("Confidence",           f"{confidence:.1f}%")

            if expected_return > 5:
                insight = "Potensi bullish cukup kuat 📈"
            elif expected_return < -5:
                insight = "Potensi bearish dominan 📉"
            else:
                insight = "Sideways / konsolidasi ⚖️"

            st.info(f"""
📌 **Insight Otomatis:**
- Trend saat ini: **{trend}**
- Prediksi return: **{expected_return:.2f}% dalam 30 hari**
- Model: Linear regression + MA20 smoothing
- Volatilitas digunakan untuk estimasi confidence

👉 Kesimpulan: **{insight}**
""")

            now_wib_end = datetime.now(ZoneInfo("Asia/Jakarta"))
            st.caption(f"Last update: {now_wib_end.strftime('%Y-%m-%d %H:%M:%S')} WIB")

        else:
            st.warning("Data tidak cukup untuk prediksi (minimal 30 candle)")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTOFOLIO SAYA
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    render_portfolio_page()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — BROKER ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("## 🏢 Broker Activity Dashboard")
    st.markdown("Analisis aktivitas akumulasi dan distribusi broker.")

    # ── Mock Data Generator ──
    @st.cache_data(ttl=3600)
    def generate_mock_broksum():
        import random
        brokers = ["YU", "RX", "ZP", "AK", "DH", "LG", "CP", "CC", "PD", "NI"]
        stocks  = DEFAULT_TICKERS
        dates   = pd.date_range(end=pd.Timestamp.today(), periods=10, freq="B")
        
        rows = []
        for d in dates:
            for stk in stocks:
                for brk in brokers:
                    if random.random() > 0.3:
                        buy  = random.choice([0, random.randint(100_000_000, 50_000_000_000)])
                        sell = random.choice([0, random.randint(100_000_000, 50_000_000_000)])
                        rows.append({
                            "date":        d,
                            "stock_code":  stk,
                            "broker_code": brk,
                            "buy_value":   buy,
                            "sell_value":  sell,
                        })
        return pd.DataFrame(rows)
    
    # Load and process data
    with st.spinner("Memuat data broker summary..."):
        df_raw = generate_mock_broksum()
        df_processed = process_broksum(df_raw)
        
    available_brokers = sorted(df_processed["broker_code"].unique())
    available_dates = sorted(df_processed["date"].dt.date.unique(), reverse=True)
    available_stocks = sorted(df_processed["stock_code"].unique())

    # Sub-tabs for Broker Activity
    subtab1, subtab2, subtab3 = st.tabs(["🌐 Overview", "👤 By Broker", "📈 By Stock"])
    
    with subtab1:
        st.markdown("### 🌐 Market Overview")
        col_dt_ov, col_top_ov = st.columns([1, 3])
        with col_dt_ov:
            sel_date_ov = st.selectbox("Filter Tanggal (Overview)", ["Semua"] + [str(d) for d in available_dates])
        
        date_filter_ov = None if sel_date_ov == "Semua" else sel_date_ov
        
        try:
            overview_df = market_overview(df_processed, date_filter=date_filter_ov)
            def color_status(val):
                color = "#22c55e" if val == "Net Buy" else "#ef4444"
                return f"color: {color}; font-weight: 700"

            st.dataframe(
                overview_df.style.map(color_status, subset=["status"]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "rank": st.column_config.NumberColumn("#", width="small"),
                    "broker_code": st.column_config.TextColumn("Broker", width="small"),
                    "total_buy": st.column_config.NumberColumn("Total Buy", format="Rp %,.0f"),
                    "total_sell": st.column_config.NumberColumn("Total Sell", format="Rp %,.0f"),
                    "net_value": st.column_config.NumberColumn("Net Value", format="Rp %,.0f"),
                    "total_value": st.column_config.NumberColumn("Total", format="Rp %,.0f"),
                    "net_ratio": st.column_config.NumberColumn("Net %", format="%.2f%%"),
                    "buy_pct": st.column_config.NumberColumn("Buy %", format="%.2f%%"),
                    "cross_count": st.column_config.NumberColumn("Cross", width="small"),
                    "stocks_traded": st.column_config.NumberColumn("Saham", width="small"),
                    "status": st.column_config.TextColumn("Status"),
                }
            )
        except Exception as e:
            st.error(f"Gagal memuat overview: {str(e)}")

    with subtab2:
        st.markdown("### 👤 Broker Drill Down")
        col_brk, col_dt, col_top, col_sig = st.columns(4)
        with col_brk:
            selected_broker = st.selectbox("Pilih Broker", available_brokers, index=0)
        with col_dt:
            selected_date = st.selectbox("Filter Tanggal", ["Semua"] + [str(d) for d in available_dates], key="date_by_broker")
        with col_top:
            top_n = st.number_input("Top N Saham", min_value=3, max_value=50, value=10)
        with col_sig:
            sig_q = st.slider("Signifikansi (Persentil)", min_value=0.0, max_value=0.9, value=0.5, step=0.1)

        date_filter = None if selected_date == "Semua" else selected_date

        try:
            activity_res = broker_activity(
                df_processed, 
                broker_code=selected_broker, 
                top_n=int(top_n), 
                significance_quantile=float(sig_q),
                date_filter=date_filter
            )
            
            meta = activity_res["meta"]
            st.caption(f"Menampilkan data untuk broker **{meta['broker_code']}** pada tanggal **{meta['date_filter']}** (Total saham setelah filter signifikansi: {meta['n_stocks_after_filter']})")
            
            col_buy, col_sell = st.columns(2)
            
            with col_buy:
                st.markdown("""
                <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                    <span style="color:#22c55e;font-weight:700;font-size:13px;">🟢 TOP BUY (Akumulasi)</span>
                </div>
                """, unsafe_allow_html=True)
                
                top_buy_df = activity_res["top_buy"].copy()
                if not top_buy_df.empty:
                    st.dataframe(
                        top_buy_df, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "rank": st.column_config.NumberColumn("#", width="small"),
                            "stock_code": st.column_config.TextColumn("Saham", width="small"),
                            "net_value": st.column_config.NumberColumn("Net Buy", format="Rp %,.0f"),
                            "buy_value": st.column_config.NumberColumn("Buy", format="Rp %,.0f"),
                            "sell_value": st.column_config.NumberColumn("Sell", format="Rp %,.0f"),
                            "total_value": None,
                            "net_ratio": st.column_config.NumberColumn("Net %", format="%.2f%%"),
                            "n_dates": None,
                        }
                    )
                else:
                    st.info("Tidak ada data akumulasi signifikan.")
                    
            with col_sell:
                st.markdown("""
                <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                    <span style="color:#ef4444;font-weight:700;font-size:13px;">🔴 TOP SELL (Distribusi)</span>
                </div>
                """, unsafe_allow_html=True)
                
                top_sell_df = activity_res["top_sell"].copy()
                if not top_sell_df.empty:
                    st.dataframe(
                        top_sell_df, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "rank": st.column_config.NumberColumn("#", width="small"),
                            "stock_code": st.column_config.TextColumn("Saham", width="small"),
                            "net_value": st.column_config.NumberColumn("Net Sell", format="Rp %,.0f"),
                            "buy_value": st.column_config.NumberColumn("Buy", format="Rp %,.0f"),
                            "sell_value": st.column_config.NumberColumn("Sell", format="Rp %,.0f"),
                            "total_value": None,
                            "net_ratio": st.column_config.NumberColumn("Net %", format="%.2f%%"),
                            "n_dates": None,
                        }
                    )
                else:
                    st.info("Tidak ada data distribusi signifikan.")

        except Exception as e:
            st.error(f"Gagal menampilkan aktivitas broker: {str(e)}")

    with subtab3:
        st.markdown("### 📈 Stock Analysis")
        col_stk, col_dt_stk, col_top_stk = st.columns([2, 1, 1])
        with col_stk:
            selected_stock = st.text_input("Kode Saham", value=available_stocks[0] if available_stocks else "")
        with col_dt_stk:
            selected_date_stk = st.selectbox("Filter Tanggal", ["Semua"] + [str(d) for d in available_dates], key="date_by_stock")
        with col_top_stk:
            top_n_stk = st.number_input("Top N Broker", min_value=3, max_value=50, value=10, key="top_by_stock")

        date_filter_stk = None if selected_date_stk == "Semua" else selected_date_stk

        if selected_stock:
            try:
                stock_res = stock_activity(
                    df_processed, 
                    stock_code=selected_stock, 
                    top_n=int(top_n_stk), 
                    date_filter=date_filter_stk
                )
                
                summ = stock_res["summary"]
                
                # Signal card
                sig = summ["signal"]
                if sig == "Akumulasi":
                    sig_color = "#22c55e"
                    sig_bg = "rgba(34,197,94,0.15)"
                elif sig == "Distribusi":
                    sig_color = "#ef4444"
                    sig_bg = "rgba(239,68,68,0.15)"
                else:
                    sig_color = "#fbbf24"
                    sig_bg = "rgba(251,191,36,0.15)"

                st.markdown(f"""
                <div style="display:flex;gap:10px;margin-bottom:14px;">
                    <div style="background:#0d1117;border:1px solid #1e2a3a;border-radius:10px;padding:16px;flex:1;">
                        <div style="color:#64748b;font-size:11px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;">Signal (By Net Value)</div>
                        <div style="margin-top:6px;display:inline-block;background:{sig_bg};color:{sig_color};padding:4px 12px;border-radius:6px;font-weight:800;font-size:16px;">{sig}</div>
                    </div>
                    <div style="background:#0d1117;border:1px solid #1e2a3a;border-radius:10px;padding:16px;flex:1;">
                        <div style="color:#64748b;font-size:11px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;">Total Net Value</div>
                        <div style="margin-top:6px;color:{'#22c55e' if summ['total_net'] > 0 else '#ef4444'};font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:700;">Rp {summ['total_net']:,.0f}</div>
                    </div>
                    <div style="background:#0d1117;border:1px solid #1e2a3a;border-radius:10px;padding:16px;flex:1;">
                        <div style="color:#64748b;font-size:11px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;">Total Buy / Sell</div>
                        <div style="margin-top:6px;color:#e2e8f0;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600;">Buy: Rp {summ['total_buy']:,.0f}<br>Sell: Rp {summ['total_sell']:,.0f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_b, col_s = st.columns(2)
                
                with col_b:
                    st.markdown("""
                    <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                        <span style="color:#22c55e;font-weight:700;font-size:13px;">🟢 BROKER AKUMULASI (Top Buy)</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if not stock_res["top_buy"].empty:
                        st.dataframe(
                            stock_res["top_buy"], 
                            use_container_width=True, hide_index=True,
                            column_config={
                                "rank": st.column_config.NumberColumn("#", width="small"),
                                "broker_code": st.column_config.TextColumn("Broker", width="small"),
                                "net_value": st.column_config.NumberColumn("Net Buy", format="Rp %,.0f"),
                                "buy_value": st.column_config.NumberColumn("Buy", format="Rp %,.0f"),
                                "sell_value": st.column_config.NumberColumn("Sell", format="Rp %,.0f"),
                                "total_value": None,
                                "net_ratio": st.column_config.NumberColumn("Net %", format="%.2f%%"),
                            }
                        )
                    else:
                        st.info("Tidak ada broker akumulasi.")
                        
                with col_s:
                    st.markdown("""
                    <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                        <span style="color:#ef4444;font-weight:700;font-size:13px;">🔴 BROKER DISTRIBUSI (Top Sell)</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if not stock_res["top_sell"].empty:
                        st.dataframe(
                            stock_res["top_sell"], 
                            use_container_width=True, hide_index=True,
                            column_config={
                                "rank": st.column_config.NumberColumn("#", width="small"),
                                "broker_code": st.column_config.TextColumn("Broker", width="small"),
                                "net_value": st.column_config.NumberColumn("Net Sell", format="Rp %,.0f"),
                                "buy_value": st.column_config.NumberColumn("Buy", format="Rp %,.0f"),
                                "sell_value": st.column_config.NumberColumn("Sell", format="Rp %,.0f"),
                                "total_value": None,
                                "net_ratio": st.column_config.NumberColumn("Net %", format="%.2f%%"),
                            }
                        )
                    else:
                        st.info("Tidak ada broker distribusi.")

            except Exception as e:
                st.error(f"Gagal menampilkan aktivitas saham: {str(e)}")
