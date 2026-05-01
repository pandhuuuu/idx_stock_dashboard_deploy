import streamlit as st
import yfinance as yf
from core.data.fetcher import fetch_data

@st.cache_data(ttl=60)
def cached_fetch(ticker_jk, period, interval):
    return fetch_data(ticker_jk, period=period, interval=interval)

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
