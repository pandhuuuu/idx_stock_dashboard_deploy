import streamlit as st

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


def render_summary_cards(df_r):
    """Render 4-column summary cards with mini progress bars."""
    total  = max(len(df_r), 1)
    n_buy  = int((df_r["Signal"] == "BUY").sum())
    n_sell = int((df_r["Signal"] == "SELL").sum())
    n_hold = int((df_r["Signal"] == "HOLD").sum())

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
        st.markdown(_card("Bullish Candidates", f"{n_buy}", f"{pct_buy}% dari total market", pct_buy, "#22c55e", "#22c55e"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_card("Bearish Candidates", f"{n_sell}", f"{pct_sell}% dari total market", pct_sell, "#ef4444", "#ef4444"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(_card("Neutral / Hold", f"{n_hold}", f"{pct_hold}% dari total market", pct_hold, "#eab308", "#eab308"), unsafe_allow_html=True)
    with cols[3]:
        # Market Sentiment Logic
        if pct_buy > pct_sell + 10:
            sent_label, sent_val, sent_sub, sent_color = ("Market Sentiment", "BULLISH", "Dominasi akumulasi", "#22c55e")
        elif pct_sell > pct_buy + 10:
            sent_label, sent_val, sent_sub, sent_color = ("Market Sentiment", "BEARISH", "Dominasi distribusi", "#ef4444")
        else:
            sent_label, sent_val, sent_sub, sent_color = ("Market Sentiment", "NEUTRAL", "Volume seimbang", "#eab308")
        st.markdown(_card(sent_label, sent_val, sent_sub, 100, sent_color, sent_color), unsafe_allow_html=True)
