"""
portfolio_page.py
─────────────────────────────────────────────────────────────────────────────
Halaman "Portofolio Saya" — LOCAL MODE (no database, st.session_state only)
─────────────────────────────────────────────────────────────────────────────
HOW TO INTEGRATE  (tambahkan di app utama kamu):

    from portfolio_page import render_portfolio_page

    tab1, tab2 = st.tabs(["📊 Scanner", "💼 Portofolio Saya"])
    with tab1:
        # ...kode scanner kamu yang ada...
        pass
    with tab2:
        render_portfolio_page()

─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Daftar emiten yang didukung beserta suffix .JK-nya
# Kamu bisa perluas list ini sesuai kebutuhan
SUPPORTED_TICKERS = [
    "BBCA", "BBRI", "BMRI", "BNGA", "BRIS", "BBNI",
    "TLKM", "EXCL", "ISAT",
    "ADRO", "PTBA", "PGAS", "MEDC", "ITMG", "PTRO",
    "ANTM", "MDKA", "INCO", "BRMS",
    "UNVR", "ICBP", "INDF", "MYOR",
    "GOTO", "WIFI",
    "ASII", "AUTO", "AALI", "LSIP",
    "SMGR", "INTP", "WIKA", "ADHI",
    "SIDO", "KLBF", "KAEF", "MIKA",
    "WBSA",
]

COMMON_EMITENS = sorted(SUPPORTED_TICKERS)

LOTS_TO_SHARES = 100  # 1 lot = 100 lembar saham


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE BOOTSTRAP
# ─────────────────────────────────────────────────────────────────────────────

def _init_session():
    """Pastikan semua key session state sudah ada."""
    if "transactions" not in st.session_state:
        st.session_state["transactions"] = []

    if "portfolio_prices" not in st.session_state:
        st.session_state["portfolio_prices"] = {}


# ─────────────────────────────────────────────────────────────────────────────
# YFINANCE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _to_jk(emiten: str) -> str:
    """Tambahkan .JK suffix jika belum ada."""
    emiten = emiten.strip().upper()
    return emiten if emiten.endswith(".JK") else f"{emiten}.JK"


def fetch_current_price(emiten: str) -> float | None:
    """
    Ambil harga terakhir dari yfinance.
    Return None kalau gagal.
    """
    try:
        ticker_jk = _to_jk(emiten)
        tk = yf.Ticker(ticker_jk)
        hist = tk.history(period="2d", interval="1d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def refresh_all_prices(emitens: list[str]) -> dict:
    """
    Ambil harga untuk semua emiten di portofolio.
    Simpan ke session_state["portfolio_prices"].
    """
    prices = {}
    for em in emitens:
        price = fetch_current_price(em)
        prices[em] = price
    st.session_state["portfolio_prices"] = prices
    return prices


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION CRUD
# ─────────────────────────────────────────────────────────────────────────────

def add_transaction(emiten: str, tx_type: str, harga: float, lot: int):
    """Tambah transaksi baru ke session state."""
    tx = {
        "id": len(st.session_state["transactions"]),   # simple auto-increment id
        "emiten": emiten.upper(),
        "type": tx_type,           # "BUY" or "SELL"
        "harga": harga,
        "lot": lot,
        "saham": lot * LOTS_TO_SHARES,
        "total": harga * lot * LOTS_TO_SHARES,
        "created_at": datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M"),
    }
    st.session_state["transactions"].append(tx)


def delete_transaction(tx_id: int):
    """Hapus transaksi berdasarkan id."""
    st.session_state["transactions"] = [
        t for t in st.session_state["transactions"] if t["id"] != tx_id
    ]


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def calculate_portfolio() -> pd.DataFrame:
    """
    Hitung posisi bersih, avg buy price, dan P/L dari semua transaksi.
    Return DataFrame portfolio aktif (net lot > 0).
    """
    txs = st.session_state["transactions"]
    if not txs:
        return pd.DataFrame()

    emitens = list({t["emiten"] for t in txs})
    rows = []

    for em in emitens:
        buy_txs  = [t for t in txs if t["emiten"] == em and t["type"] == "BUY"]
        sell_txs = [t for t in txs if t["emiten"] == em and t["type"] == "SELL"]

        total_buy_lot  = sum(t["lot"] for t in buy_txs)
        total_sell_lot = sum(t["lot"] for t in sell_txs)
        net_lot        = total_buy_lot - total_sell_lot

        if net_lot <= 0:
            continue  # posisi sudah ditutup / over-sell → skip

        # Weighted average buy price
        total_buy_value  = sum(t["harga"] * t["lot"] for t in buy_txs)
        avg_buy          = total_buy_value / total_buy_lot if total_buy_lot else 0

        net_shares = net_lot * LOTS_TO_SHARES
        modal      = avg_buy * net_shares

        # Harga market dari cache
        market_price = st.session_state["portfolio_prices"].get(em)

        if market_price:
            nilai_sekarang = market_price * net_shares
            pl_rp          = nilai_sekarang - modal
            pl_pct         = (pl_rp / modal * 100) if modal else 0
        else:
            nilai_sekarang = None
            pl_rp          = None
            pl_pct         = None

        rows.append({
            "Emiten":         em,
            "Net Lot":        net_lot,
            "Net Saham":      net_shares,
            "Avg Buy":        round(avg_buy, 2),
            "Harga Sekarang": market_price,
            "Modal (Rp)":     round(modal, 0),
            "Nilai Skrg (Rp)": round(nilai_sekarang, 0) if nilai_sekarang else None,
            "P/L (Rp)":       round(pl_rp, 0) if pl_rp is not None else None,
            "P/L (%)":        round(pl_pct, 2) if pl_pct is not None else None,
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# DECISION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def get_decision(pl_pct: float | None) -> tuple[str, str]:
    """
    Return (keputusan_emoji, alasan) berdasarkan persentase P/L.
    """
    if pl_pct is None:
        return "⏳ MENUNGGU DATA", "Harga pasar belum tersedia. Klik Refresh Harga."

    if pl_pct > 10:
        return "💰 TAKE PROFIT", f"Profit {pl_pct:.1f}% sudah melampaui target +10%. Pertimbangkan untuk merealisasikan keuntungan."
    elif pl_pct >= 5:
        return "📈 AVERAGE UP", f"Profit {pl_pct:.1f}% kuat. Bisa tambah posisi mengikuti momentum naik."
    elif pl_pct > -5:
        return "🤝 HOLD", f"Perubahan {pl_pct:.1f}% masih dalam range normal (-5% s/d +5%). Pertahankan posisi."
    elif pl_pct >= -15:
        return "🔽 AVERAGE DOWN", f"Koreksi {pl_pct:.1f}% dalam kisaran -5% s/d -15%. Pertimbangkan menambah lot untuk menurunkan avg buy."
    else:
        return "🔪 CUT LOSS", f"Loss {pl_pct:.1f}% sudah melewati batas -15%. Segera evaluasi dan pertimbangkan cut loss."


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def get_summary(df_portfolio: pd.DataFrame) -> dict:
    """Hitung total summary portfolio."""
    if df_portfolio.empty:
        return {}

    total_modal  = df_portfolio["Modal (Rp)"].sum()
    total_nilai  = df_portfolio["Nilai Skrg (Rp)"].dropna().sum()
    total_pl     = df_portfolio["P/L (Rp)"].dropna().sum()
    total_pl_pct = (total_pl / total_modal * 100) if total_modal else 0

    return {
        "total_modal":  total_modal,
        "total_nilai":  total_nilai,
        "total_pl":     total_pl,
        "total_pl_pct": total_pl_pct,
        "n_emiten":     len(df_portfolio),
    }


# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _color_pl(val):
    """Styler helper: warna hijau kalau positif, merah kalau negatif."""
    if val is None:
        return ""
    try:
        v = float(val)
        if v > 0:
            return "color: #00C853; font-weight: 600"
        elif v < 0:
            return "color: #FF5252; font-weight: 600"
    except Exception:
        pass
    return ""


def _fmt_rp(val):
    if val is None:
        return "—"
    try:
        return f"Rp {float(val):,.0f}"
    except Exception:
        return "—"


def _fmt_pct(val):
    if val is None:
        return "—"
    try:
        v = float(val)
        arrow = "▲" if v >= 0 else "▼"
        return f"{arrow} {abs(v):.2f}%"
    except Exception:
        return "—"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER FUNCTION — panggil ini dari app utama
# ─────────────────────────────────────────────────────────────────────────────

def render_portfolio_page():
    """
    Render seluruh halaman Portofolio Saya.
    Panggil fungsi ini di dalam tab atau page Streamlit kamu.
    """
    _init_session()

    # ── CSS khusus portfolio (melengkapi CSS global app) ──────────────────────
    st.markdown("""
    <style>
        .port-card {
            background: #1a1d27;
            border: 1px solid #2a2d3e;
            border-radius: 12px;
            padding: 18px 22px;
            margin-bottom: 8px;
        }
        .port-card-title {
            color: #8b8fa8;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }
        .port-card-value {
            font-size: 26px;
            font-weight: 700;
        }
        .decision-box {
            border-radius: 10px;
            padding: 12px 18px;
            margin: 6px 0;
            border-left: 4px solid;
        }
        .decision-tp  { background: #0d2b1a; border-color: #00C853; }
        .decision-cl  { background: #2b0d0d; border-color: #FF5252; }
        .decision-hold{ background: #1a1d27; border-color: #4f8ef7; }
        .decision-au  { background: #112b1a; border-color: #00E5FF; }
        .decision-ad  { background: #1a1a0d; border-color: #FFD600; }
        .tx-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #13151f;
            border: 1px solid #2a2d3e;
            border-radius: 8px;
            padding: 10px 16px;
            margin-bottom: 6px;
            font-size: 14px;
        }
        .badge-buy  { background:#00C853;color:#000;border-radius:5px;padding:2px 8px;font-weight:700;font-size:12px; }
        .badge-sell { background:#FF5252;color:#fff;border-radius:5px;padding:2px 8px;font-weight:700;font-size:12px; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("## 💼 Portofolio Saya")
    st.caption("Semua data tersimpan di session lokal — tidak ada database. Data hilang saat halaman ditutup.")

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — INPUT TRANSAKSI
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### ➕ Input Transaksi")

    with st.container():
        c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.8, 1.5, 1.2])

        with c1:
            emiten_input = st.selectbox(
                "Emiten",
                options=COMMON_EMITENS,
                key="form_emiten",
                help="Pilih atau ketik kode saham"
            )
        with c2:
            tx_type = st.selectbox(
                "Transaksi",
                options=["BUY", "SELL"],
                key="form_type"
            )
        with c3:
            harga_input = st.number_input(
                "Harga per Saham (Rp)",
                min_value=1.0,
                value=1000.0,
                step=50.0,
                format="%.0f",
                key="form_harga"
            )
        with c4:
            lot_input = st.number_input(
                "Jumlah Lot",
                min_value=1,
                value=1,
                step=1,
                key="form_lot"
            )
        with c5:
            st.markdown("<br>", unsafe_allow_html=True)  # spacer
            add_btn = st.button("✅ Tambah", use_container_width=True, key="btn_add_tx")

    # Preview nilai transaksi
    preview_total = harga_input * lot_input * LOTS_TO_SHARES
    st.caption(f"💡 Estimasi total: **Rp {preview_total:,.0f}** ({lot_input} lot × {LOTS_TO_SHARES} saham × Rp {harga_input:,.0f})")

    # Submit handler
    if add_btn:
        # Validasi
        if lot_input <= 0:
            st.error("Jumlah lot harus lebih dari 0")
        elif harga_input <= 0:
            st.error("Harga harus lebih dari 0")
        else:
            # Cek over-sell guard
            if tx_type == "SELL":
                existing_buy_lot  = sum(
                    t["lot"] for t in st.session_state["transactions"]
                    if t["emiten"] == emiten_input.upper() and t["type"] == "BUY"
                )
                existing_sell_lot = sum(
                    t["lot"] for t in st.session_state["transactions"]
                    if t["emiten"] == emiten_input.upper() and t["type"] == "SELL"
                )
                if (existing_sell_lot + lot_input) > existing_buy_lot:
                    st.error(
                        f"❌ SELL melebihi posisi BUY. "
                        f"Posisi bersih kamu: {existing_buy_lot - existing_sell_lot} lot."
                    )
                    st.stop()

            add_transaction(emiten_input, tx_type, harga_input, lot_input)
            st.success(f"✅ Transaksi {tx_type} {emiten_input} {lot_input} lot @ Rp {harga_input:,.0f} berhasil disimpan!")
            st.rerun()

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — REFRESH HARGA & PORTFOLIO CALCULATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Ambil semua emiten aktif
    all_emitens_in_tx = list({
        t["emiten"] for t in st.session_state["transactions"]
    })

    col_refresh, col_info = st.columns([1, 3])
    with col_refresh:
        refresh_btn = st.button("🔄 Refresh Harga", use_container_width=True, key="btn_refresh")

    if refresh_btn and all_emitens_in_tx:
        with st.spinner("Mengambil harga dari yfinance..."):
            prices = refresh_all_prices(all_emitens_in_tx)
        fetched = [k for k, v in prices.items() if v is not None]
        failed  = [k for k, v in prices.items() if v is None]
        msg = f"✅ Harga berhasil diambil: {', '.join(fetched)}"
        if failed:
            msg += f"  |  ⚠️ Gagal: {', '.join(failed)}"
        with col_info:
            st.info(msg)
    elif refresh_btn and not all_emitens_in_tx:
        with col_info:
            st.warning("Belum ada transaksi. Tambah transaksi dulu.")

    # Hitung portfolio
    df_portfolio = calculate_portfolio()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════
    if not df_portfolio.empty:
        summary = get_summary(df_portfolio)

        st.markdown("### 📊 Summary Portfolio")
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)

        def _summary_card(col, title, value, color="#fff"):
            col.markdown(f"""
            <div class="port-card">
                <div class="port-card-title">{title}</div>
                <div class="port-card-value" style="color:{color}">{value}</div>
            </div>
            """, unsafe_allow_html=True)

        _summary_card(sc1, "💰 Total Modal", _fmt_rp(summary["total_modal"]))
        _summary_card(sc2, "📈 Nilai Sekarang", _fmt_rp(summary["total_nilai"]))

        pl_color = "#00C853" if summary["total_pl"] >= 0 else "#FF5252"
        _summary_card(sc3, "💵 Total P/L (Rp)", _fmt_rp(summary["total_pl"]), pl_color)
        _summary_card(sc4, "📊 Total P/L (%)", _fmt_pct(summary["total_pl_pct"]), pl_color)
        _summary_card(sc5, "🏢 Emiten Aktif", str(summary["n_emiten"]))

        st.markdown("---")

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 4 — PORTFOLIO TABLE + DECISION
        # ═══════════════════════════════════════════════════════════════════════
        st.markdown("### 📋 Posisi Aktif & Keputusan")

        for _, row in df_portfolio.iterrows():
            em        = row["Emiten"]
            pl_pct    = row["P/L (%)"]
            pl_rp     = row["P/L (Rp)"]
            avg_buy   = row["Avg Buy"]
            mkt_price = row["Harga Sekarang"]
            modal     = row["Modal (Rp)"]

            decision, reason = get_decision(pl_pct)

            # Warna card keputusan
            if "TAKE PROFIT" in decision:
                box_class = "decision-tp"
            elif "CUT LOSS" in decision:
                box_class = "decision-cl"
            elif "AVERAGE UP" in decision:
                box_class = "decision-au"
            elif "AVERAGE DOWN" in decision:
                box_class = "decision-ad"
            else:
                box_class = "decision-hold"

            pl_color_hex = "#00C853" if (pl_pct or 0) >= 0 else "#FF5252"

            with st.expander(
                f"**{em}** — {decision}  |  "
                f"{'▲' if (pl_pct or 0) >= 0 else '▼'} {abs(pl_pct or 0):.2f}%  "
                f"({_fmt_rp(pl_rp)})",
                expanded=True
            ):
                dc1, dc2, dc3, dc4, dc5 = st.columns(5)
                dc1.metric("Avg Buy",       f"Rp {avg_buy:,.0f}")
                dc2.metric("Harga Pasar",   f"Rp {mkt_price:,.0f}" if mkt_price else "—")
                dc3.metric("Net Lot",       row["Net Lot"])
                dc4.metric("P/L (Rp)",      _fmt_rp(pl_rp),
                           delta=_fmt_pct(pl_pct) if pl_pct is not None else None)
                dc5.metric("Modal",         _fmt_rp(modal))

                st.markdown(f"""
                <div class="decision-box {box_class}">
                    <strong>{decision}</strong><br>
                    <small style="color:#aaa">{reason}</small>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 5 — FULL PORTFOLIO DATAFRAME (styled)
        # ═══════════════════════════════════════════════════════════════════════
        st.markdown("### 🗂️ Tabel Portfolio Lengkap")

        df_show = df_portfolio.copy()

        # Format kolom untuk display
        df_show["Avg Buy"]          = df_show["Avg Buy"].apply(lambda v: f"Rp {v:,.0f}")
        df_show["Modal (Rp)"]       = df_show["Modal (Rp)"].apply(lambda v: f"Rp {v:,.0f}" if v else "—")
        df_show["Nilai Skrg (Rp)"]  = df_show["Nilai Skrg (Rp)"].apply(lambda v: f"Rp {v:,.0f}" if v else "—")
        df_show["P/L (Rp)"]         = df_show["P/L (Rp)"].apply(_fmt_rp)
        df_show["P/L (%)"]          = df_show["P/L (%)"].apply(_fmt_pct)
        df_show["Harga Sekarang"]   = df_show["Harga Sekarang"].apply(
            lambda v: f"Rp {v:,.0f}" if v else "⚠️ Belum refresh"
        )
        df_show["Keputusan"] = df_portfolio["P/L (%)"].apply(
            lambda v: get_decision(v)[0]
        )

        st.dataframe(df_show, use_container_width=True, hide_index=True)

    else:
        if st.session_state["transactions"]:
            # Ada transaksi tapi semua sudah SELL
            st.info("ℹ️ Semua posisi sudah tertutup (net lot = 0). Tambah transaksi BUY untuk mulai portofolio baru.")
        else:
            st.info("💡 Belum ada transaksi. Gunakan form di atas untuk mencatat transaksi pertama kamu.")

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — RIWAYAT TRANSAKSI + DELETE
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📜 Riwayat Transaksi")

    txs = st.session_state["transactions"]

    if not txs:
        st.caption("Belum ada transaksi.")
    else:
        # Header
        hcols = st.columns([0.5, 1.5, 1, 1.5, 1, 1.5, 2, 1])
        headers = ["#", "Emiten", "Type", "Harga", "Lot", "Total (Rp)", "Waktu", "Hapus"]
        for col, h in zip(hcols, headers):
            col.markdown(f"<small style='color:#8b8fa8'><b>{h}</b></small>", unsafe_allow_html=True)

        st.markdown("<hr style='margin:4px 0;border-color:#2a2d3e'>", unsafe_allow_html=True)

        for i, tx in enumerate(reversed(txs)):  # terbaru di atas
            cols = st.columns([0.5, 1.5, 1, 1.5, 1, 1.5, 2, 1])
            badge = (
                '<span class="badge-buy">BUY</span>'
                if tx["type"] == "BUY"
                else '<span class="badge-sell">SELL</span>'
            )
            cols[0].markdown(f"<small>{len(txs) - i}</small>", unsafe_allow_html=True)
            cols[1].markdown(f"**{tx['emiten']}**")
            cols[2].markdown(badge, unsafe_allow_html=True)
            cols[3].markdown(f"`Rp {tx['harga']:,.0f}`")
            cols[4].markdown(f"{tx['lot']} lot")
            cols[5].markdown(f"Rp {tx['total']:,.0f}")
            cols[6].markdown(f"<small>{tx['created_at']}</small>", unsafe_allow_html=True)

            if cols[7].button("🗑️", key=f"del_{tx['id']}_{i}", help="Hapus transaksi ini"):
                delete_transaction(tx["id"])
                st.toast(f"🗑️ Transaksi {tx['emiten']} {tx['type']} dihapus")
                st.rerun()

    # ─── Footer timestamp ───────────────────────────────────────────────────
    st.markdown("---")
    now_wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    st.caption(f"💼 Portofolio Saya  •  Data tersimpan lokal  •  {now_wib.strftime('%Y-%m-%d %H:%M:%S')} WIB")
