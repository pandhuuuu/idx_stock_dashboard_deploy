"""
broksum_processor.py
────────────────────────────────────────────────────────────────────────────
Modul untuk memproses data Broker Summary (broksum) dari Bursa Efek Indonesia.

Kolom input yang diharapkan:
    date         – tanggal transaksi (str / datetime)
    stock_code   – kode saham (str, contoh: "BBCA")
    broker_code  – kode broker (str, contoh: "YU", "RX", "ZP")
    buy_value    – nilai pembelian dalam Rupiah (numeric)
    sell_value   – nilai penjualan dalam Rupiah (numeric)

Kolom yang ditambahkan:
    net_value    – buy_value - sell_value  (+ = Net Buy, - = Net Sell)
    total_value  – buy_value + sell_value  (total transaksi dua arah)
    cross_ratio  – min(buy, sell) / max(buy, sell)  (1.0 = perfect cross)
    status       – "Net Buy" | "Net Sell" | "Neutral"
    is_cross     – True jika cross_ratio > 0.7 AND total_value ≥ threshold

Fungsi utama:
    process_broksum(df, cross_total_threshold, neutral_band)

Fungsi utilitas:
    summarize_by_stock(df)   – net per saham per tanggal
    summarize_by_broker(df)  – net per broker per tanggal
    top_net_buy(df, n)       – top-N broker accumulator
    top_net_sell(df, n)      – top-N broker distributor
    detect_cross_trades(df)  – baris dengan is_cross == True
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# KONSTANTA DEFAULT
# ─────────────────────────────────────────────────────────────────────────────

_REQUIRED_COLS: list[str] = [
    "date", "stock_code", "broker_code", "buy_value", "sell_value"
]

_DEFAULT_CROSS_THRESHOLD_QUANTILE: float = 0.75  # Persentil untuk total_value
_DEFAULT_NEUTRAL_BAND: float = 0.05              # ±5 % dari total_value


# ─────────────────────────────────────────────────────────────────────────────
# HELPER INTERNAL
# ─────────────────────────────────────────────────────────────────────────────

def _validate_columns(df: pd.DataFrame) -> None:
    """Validasi bahwa semua kolom yang dibutuhkan tersedia."""
    missing = [c for c in _REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Kolom berikut tidak ditemukan di DataFrame: {missing}\n"
            f"Kolom yang tersedia: {list(df.columns)}"
        )


def _safe_cross_ratio(buy: pd.Series, sell: pd.Series) -> pd.Series:
    """
    Hitung cross_ratio = min(buy, sell) / max(buy, sell).
    Hasil NaN jika kedua nilai 0 (tidak ada transaksi sama sekali).
    """
    lo  = pd.concat([buy, sell], axis=1).min(axis=1)
    hi  = pd.concat([buy, sell], axis=1).max(axis=1)
    # Hindari pembagian dengan nol; hasilnya NaN di baris zero-activity
    ratio = lo / hi.replace(0, np.nan)
    return ratio.clip(upper=1.0)   # cap 1.0 untuk keamanan numerik


def _assign_status(net_value: pd.Series, neutral_band: float,
                   total_value: pd.Series) -> pd.Series:
    """
    Beri label status berdasarkan net_value relatif terhadap total_value.

    Logika:
        |net_value| / total_value  ≤ neutral_band  →  "Neutral"
        net_value > 0                               →  "Net Buy"
        net_value < 0                               →  "Net Sell"
    """
    # Rasio absolut net terhadap total (hindari /0)
    abs_ratio = net_value.abs() / total_value.replace(0, np.nan)
    status = pd.Series("Neutral", index=net_value.index, dtype="object")
    status = status.where(abs_ratio <= neutral_band,
                          other=np.where(net_value > 0, "Net Buy", "Net Sell"))
    return status


# ─────────────────────────────────────────────────────────────────────────────
# FUNGSI UTAMA
# ─────────────────────────────────────────────────────────────────────────────

def process_broksum(
    df: pd.DataFrame,
    cross_total_threshold: float | None = None,
    neutral_band: float = _DEFAULT_NEUTRAL_BAND,
) -> pd.DataFrame:
    """
    Proses dan enrichment data Broker Summary BEI.

    Parameters
    ----------
    df : pd.DataFrame
        Raw broksum dengan kolom: date, stock_code, broker_code,
        buy_value, sell_value.

    cross_total_threshold : float | None
        Batas minimum total_value untuk is_cross = True.
        Jika None, otomatis menggunakan persentil ke-75 dari total_value.
        (Gunakan nilai absolut Rupiah jika ingin set manual, misal: 1_000_000_000)

    neutral_band : float
        Toleransi rasio |net_value| / total_value untuk dianggap Neutral.
        Default 0.05 (±5 %).

    Returns
    -------
    pd.DataFrame
        DataFrame yang sudah dibersihkan dan diperkaya dengan kolom:
        net_value, total_value, cross_ratio, status, is_cross.

    Raises
    ------
    ValueError
        Jika kolom wajib tidak ditemukan.
    """
    # ── 1. Validasi & salin ──────────────────────────────────────────────────
    _validate_columns(df)
    out = df.copy()

    # ── 2. Normalisasi tipe data ─────────────────────────────────────────────
    out["date"]       = pd.to_datetime(out["date"], errors="coerce")
    out["stock_code"] = out["stock_code"].astype(str).str.strip().str.upper()
    out["broker_code"]= out["broker_code"].astype(str).str.strip().str.upper()
    out["buy_value"]  = pd.to_numeric(out["buy_value"],  errors="coerce").fillna(0.0)
    out["sell_value"] = pd.to_numeric(out["sell_value"], errors="coerce").fillna(0.0)

    # ── 3. Buang baris tanggal tidak valid ───────────────────────────────────
    invalid_dates = out["date"].isna().sum()
    if invalid_dates > 0:
        print(f"[broksum_processor] WARN: {invalid_dates} baris dibuang "
              f"karena tanggal tidak valid.")
    out = out.dropna(subset=["date"]).reset_index(drop=True)

    # ── 4. Derived columns ───────────────────────────────────────────────────
    out["net_value"]   = out["buy_value"] - out["sell_value"]
    out["total_value"] = out["buy_value"] + out["sell_value"]
    out["cross_ratio"] = _safe_cross_ratio(out["buy_value"], out["sell_value"])

    # ── 5. Status label ──────────────────────────────────────────────────────
    out["status"] = _assign_status(out["net_value"], neutral_band,
                                   out["total_value"])

    # ── 6. is_cross flag ─────────────────────────────────────────────────────
    if cross_total_threshold is None:
        # Gunakan persentil ke-75 dari total_value sebagai threshold adaptif
        cross_total_threshold = out["total_value"].quantile(
            _DEFAULT_CROSS_THRESHOLD_QUANTILE
        )

    out["is_cross"] = (
        (out["cross_ratio"] > 0.70) &
        (out["total_value"] >= cross_total_threshold)
    )

    # ── 7. Urutkan & tipe akhir ───────────────────────────────────────────────
    out = out.sort_values(["date", "stock_code", "broker_code"],
                          ignore_index=True)
    out["status"]   = out["status"].astype("category")
    out["is_cross"] = out["is_cross"].astype(bool)

    # Ringkasan singkat ke konsol (opsional, hapus jika tidak perlu)
    n_total  = len(out)
    n_cross  = int(out["is_cross"].sum())
    n_buy    = int((out["status"] == "Net Buy").sum())
    n_sell   = int((out["status"] == "Net Sell").sum())
    n_neutral= int((out["status"] == "Neutral").sum())
    print(
        f"[broksum_processor] OK: {n_total} baris diproses | "
        f"Net Buy: {n_buy} | Net Sell: {n_sell} | Neutral: {n_neutral} | "
        f"Cross-trade: {n_cross} (threshold >= {cross_total_threshold:,.0f})"
    )

    return out


# ─────────────────────────────────────────────────────────────────────────────
# FUNGSI UTILITAS / AGREGASI
# ─────────────────────────────────────────────────────────────────────────────

def summarize_by_stock(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agregasi net_value dan total_value per saham per tanggal.

    Returns
    -------
    pd.DataFrame dengan kolom:
        date, stock_code, net_value, total_value, cross_count,
        dominant_status
    """
    _check_processed(df)
    grp = df.groupby(["date", "stock_code"], observed=True)
    agg = grp.agg(
        net_value   =("net_value",   "sum"),
        total_value =("total_value", "sum"),
        cross_count =("is_cross",    "sum"),
        n_brokers   =("broker_code", "nunique"),
    ).reset_index()

    # Status dominan berdasarkan net gabungan
    agg["dominant_status"] = agg["net_value"].apply(
        lambda v: "Net Buy" if v > 0 else ("Net Sell" if v < 0 else "Neutral")
    )
    return agg.sort_values(["date", "net_value"], ascending=[True, False],
                            ignore_index=True)


def summarize_by_broker(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agregasi net_value dan total_value per broker per tanggal
    (lintas semua saham).

    Returns
    -------
    pd.DataFrame dengan kolom:
        date, broker_code, net_value, total_value, cross_count,
        stocks_traded, dominant_status
    """
    _check_processed(df)
    grp = df.groupby(["date", "broker_code"], observed=True)
    agg = grp.agg(
        net_value     =("net_value",   "sum"),
        total_value   =("total_value", "sum"),
        cross_count   =("is_cross",    "sum"),
        stocks_traded =("stock_code",  "nunique"),
    ).reset_index()

    agg["dominant_status"] = agg["net_value"].apply(
        lambda v: "Net Buy" if v > 0 else ("Net Sell" if v < 0 else "Neutral")
    )
    return agg.sort_values(["date", "net_value"], ascending=[True, False],
                            ignore_index=True)


def top_net_buy(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Top-N broker dengan akumulasi bersih tertinggi
    (agregat seluruh tanggal dan saham).

    Returns
    -------
    pd.DataFrame : broker_code, net_value, buy_value, sell_value, total_value
    """
    _check_processed(df)
    agg = (
        df.groupby("broker_code", observed=True)
        .agg(
            net_value  =("net_value",   "sum"),
            buy_value  =("buy_value",   "sum"),
            sell_value =("sell_value",  "sum"),
            total_value=("total_value", "sum"),
        )
        .reset_index()
        .sort_values("net_value", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )
    return agg


def top_net_sell(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Top-N broker dengan distribusi bersih tertinggi
    (net_value paling negatif).

    Returns
    -------
    pd.DataFrame : broker_code, net_value, buy_value, sell_value, total_value
    """
    _check_processed(df)
    agg = (
        df.groupby("broker_code", observed=True)
        .agg(
            net_value  =("net_value",   "sum"),
            buy_value  =("buy_value",   "sum"),
            sell_value =("sell_value",  "sum"),
            total_value=("total_value", "sum"),
        )
        .reset_index()
        .sort_values("net_value", ascending=True)   # paling negatif di atas
        .head(n)
        .reset_index(drop=True)
    )
    return agg


def detect_cross_trades(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter baris yang terdeteksi sebagai cross-trade
    (is_cross == True), diurutkan berdasarkan total_value DESC.
    """
    _check_processed(df)
    return (
        df[df["is_cross"]]
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )


# ─────────────────────────────────────────────────────────────────────────────
# GUARD: pastikan df sudah diproses sebelum agregasi
# ─────────────────────────────────────────────────────────────────────────────

def _check_processed(df: pd.DataFrame) -> None:
    derived_cols = ["net_value", "total_value", "cross_ratio", "status", "is_cross"]
    missing = [c for c in derived_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"DataFrame belum diproses oleh process_broksum(). "
            f"Kolom yang hilang: {missing}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# QUICK DEMO  (python broksum_processor.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random, string

    random.seed(42)
    np.random.seed(42)

    brokers    = ["YU", "RX", "ZP", "AK", "DH", "LG", "CP"]
    stocks     = ["BBCA", "BBRI", "BMRI", "TLKM", "GOTO", "ANTM"]
    dates      = pd.date_range("2025-01-02", periods=20, freq="B")

    rows = []
    for d in dates:
        for stk in stocks:
            for brk in brokers:
                buy  = random.choice([0, random.randint(100_000_000, 10_000_000_000)])
                sell = random.choice([0, random.randint(100_000_000, 10_000_000_000)])
                rows.append({
                    "date":        d,
                    "stock_code":  stk,
                    "broker_code": brk,
                    "buy_value":   buy,
                    "sell_value":  sell,
                })

    raw = pd.DataFrame(rows)
    print("-" * 60)
    print(f"Raw data: {len(raw)} baris")
    print("-" * 60)

    processed = process_broksum(raw)

    print("\n-- Sample output (5 baris) --")
    print(processed[[
        "date", "stock_code", "broker_code",
        "buy_value", "sell_value",
        "net_value", "total_value", "cross_ratio",
        "status", "is_cross"
    ]].head(5).to_string(index=False))

    print("\n-- Ringkasan per Saham (3 baris) --")
    print(summarize_by_stock(processed).head(3).to_string(index=False))

    print("\n-- Top 5 Net Buy Broker --")
    print(top_net_buy(processed, n=5).to_string(index=False))

    print("\n-- Top 5 Net Sell Broker --")
    print(top_net_sell(processed, n=5).to_string(index=False))

    print("\n-- Cross-Trade Terdeteksi --")
    ct = detect_cross_trades(processed)
    print(f"Total cross-trade rows: {len(ct)}")
    print(ct.head(5).to_string(index=False))
