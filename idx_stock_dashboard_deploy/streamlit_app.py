import streamlit as st
from idx_stock_monitor import fetch_data, calculate_signals, add_jk

st.title("📊 IDX Stock Monitor")

tickers = st.text_input("Masukkan saham (pisah koma)", "BBCA,BBRI,TLKM")

if st.button("Scan"):
    results = []

    for t in tickers.split(","):
        t = t.strip()
        df = fetch_data(add_jk(t))

        if df is not None:
            sig = calculate_signals(df)
            results.append({
                "Saham": t,
                "Harga": sig["price"],
                "RSI": sig["rsi"],
                "Signal": "BUY" if sig["bull_score"] > sig["bear_score"] else "SELL"
            })

    st.dataframe(results)
