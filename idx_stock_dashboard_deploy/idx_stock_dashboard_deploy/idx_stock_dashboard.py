import streamlit as st
import pandas as pd
import talib
from datetime import datetime

from idx_stock_monitor import add_jk, fetch_data, calculate_signals, DEFAULT_TICKERS

st.set_page_config(
    page_title="IDX Stock Dashboard",
    page_icon="📈",
    layout="wide",
)

DEFAULT_UI_TICKERS = DEFAULT_TICKERS[:12]

@st.cache_data(show_spinner=False)
def load_ticker_data(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    ticker_jk = add_jk(ticker)
    return fetch_data(ticker_jk, period=period, interval=interval)

@st.cache_data(show_spinner=False)
def calculate_ticker_signal(ticker: str, period: str, interval: str) -> dict | None:
    df = load_ticker_data(ticker, period, interval)
    if df is None:
        return None
    sig = calculate_signals(df)
    sig["ticker"] = ticker
    return sig

@st.cache_data(show_spinner=False)
def build_signal_table(tickers: list[str], period: str, interval: str) -> pd.DataFrame:
    records = []
    for ticker in tickers:
        result = calculate_ticker_signal(ticker, period, interval)
        if result is None:
            records.append({
                "Ticker": ticker,
                "Price": "NO DATA",
                "RSI(14)": "-",
                "Stoch K": "-",
                "Vol x": "-",
                "ATR %": "-",
                "Signal": "NO DATA",
                "Confidence": "-",
                "Details": "Data tidak tersedia",
                "SL": "-",
                "TP": "-",
                "R/R": "-",
            })
        else:
            records.append({
                "Ticker": ticker,
                "Price": f"{result['price']:,.0f}",
                "RSI(14)": result["rsi"],
                "Stoch K": result["stoch_k"],
                "Vol x": result["rvol"],
                "ATR %": result["atr_pct"],
                "Signal": "BUY" if result["bull_score"] > result["bear_score"] else "SELL" if result["bear_score"] > result["bull_score"] else "NEUTRAL",
                "Confidence": result["confidence"],
                "Details": " | ".join(result["signals"][:4]) if result["signals"] else "No signals",
                "SL": f"{result['suggested_sl']:,.0f}",
                "TP": f"{result['suggested_tp']:,.0f}",
                "R/R": f"{result['risk_reward']:.2f}",
            })
    return pd.DataFrame(records)

@st.cache_data(show_spinner=False)
def load_detail_chart_data(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    df = load_ticker_data(ticker, period, interval)
    if df is None:
        return None
    close = df["Close"].astype(float)
    rsi = talib.RSI(close, timeperiod=14)
    macd_line, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    detail = pd.DataFrame(
        {
            "Close": close,
            "RSI(14)": rsi,
            "MACD": macd_line,
            "MACD Signal": macd_signal,
        },
        index=df.index,
    )
    return detail


def render_market_overview(df: pd.DataFrame) -> tuple[str, str]:
    buy_count = len(df[df["Signal"] == "BUY"])
    sell_count = len(df[df["Signal"] == "SELL"])
    neutral_count = len(df[df["Signal"] == "NEUTRAL"])
    total = len(df)

    buy_pct = buy_count / total * 100 if total else 0
    sell_pct = sell_count / total * 100 if total else 0

    if buy_pct > sell_pct + 10:
        return "🐂 BULLISH", "success"
    if sell_pct > buy_pct + 10:
        return "🐻 BEARISH", "error"
    return "⚖️ NEUTRAL", "warning"


def main() -> None:
    st.title("IDX Stock Entry Dashboard")
    st.write("Web dashboard untuk analisis teknikal saham IDX dengan indikator multi-faktor.")

    with st.sidebar:
        st.header("Filter & Pengaturan")
        selected_tickers = st.multiselect(
            "Pilih saham IDX",
            options=DEFAULT_TICKERS,
            default=DEFAULT_UI_TICKERS,
            help="Pilih kode saham tanpa .JK."
        )
        period = st.selectbox("Periode data", ["1mo", "3mo", "6mo", "1y"], index=1)
        interval = st.selectbox("Interval candle", ["1d", "1wk"], index=0)
        st.caption("Gunakan tombol refresh browser untuk memuat ulang atau ubah filter untuk scan ulang.")

    if not selected_tickers:
        st.warning("Pilih minimal satu ticker untuk memulai scan.")
        return

    placeholder = st.empty()
    progress_bar = placeholder.progress(0)

    with st.spinner("Mengumpulkan data dan menghitung sinyal..."):
        signal_df = build_signal_table(selected_tickers, period, interval)
        progress_bar.progress(100)

    placeholder.empty()

    if signal_df.empty:
        st.error("Tidak ada data signal yang berhasil dihitung.")
        return

    sentiment, sentiment_level = render_market_overview(signal_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("BUY", f"{len(signal_df[signal_df['Signal'] == 'BUY'])}")
    col2.metric("SELL", f"{len(signal_df[signal_df['Signal'] == 'SELL'])}")
    col3.metric("NEUTRAL", f"{len(signal_df[signal_df['Signal'] == 'NEUTRAL'])}")
    col4.metric("Market Sentiment", sentiment)

    st.markdown("---")

    st.subheader("Ringkasan Sinyal")
    st.markdown(
        f"- **Periode**: {period} · **Interval**: {interval} · **Total saham**: {len(signal_df)}\n"
        f"- **Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    st.dataframe(signal_df, width='stretch')

    st.subheader("Top Kandidat Entry / Exit")
    buy_list = signal_df[signal_df["Signal"] == "BUY"]["Ticker"].tolist()[:5]
    sell_list = signal_df[signal_df["Signal"] == "SELL"]["Ticker"].tolist()[:5]

    st.markdown(
        "**Top Entry Candidates:** " + (", ".join(buy_list) if buy_list else "Tidak ada BUY signal")
    )
    st.markdown(
        "**Exit / Avoid Candidates:** " + (", ".join(sell_list) if sell_list else "Tidak ada SELL signal")
    )

    st.markdown("---")

    st.subheader("Detail Saham")
    detail_ticker = st.selectbox("Pilih saham untuk melihat chart dan data historis", selected_tickers)
    detail_data = load_detail_chart_data(detail_ticker, period, interval)

    if detail_data is None:
        st.warning("Data historis tidak tersedia untuk ticker ini.")
    else:
        st.markdown(f"### {detail_ticker}.JK")
        st.line_chart(detail_data[["Close"]])
        st.line_chart(detail_data[["RSI(14)"]].dropna())
        st.line_chart(detail_data[["MACD", "MACD Signal"]].dropna())

    st.markdown("---")
    st.caption("Dashboard ini hanya untuk tujuan edukasi dan analisis. Bukan rekomendasi investasi.")


if __name__ == "__main__":
    main()
