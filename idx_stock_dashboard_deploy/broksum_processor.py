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
# BROKER ACTIVITY  —  aktivitas per saham untuk broker tertentu
# ─────────────────────────────────────────────────────────────────────────────

def broker_activity(
    df: pd.DataFrame,
    broker_code: str,
    top_n: int = 10,
    significance_quantile: float = 0.50,
    date_filter: "str | pd.Timestamp | None" = None,
) -> dict[str, pd.DataFrame]:
    """
    Tampilkan aktivitas broker tertentu per saham, dipisah menjadi
    Top Buy (net terbesar) dan Top Sell (net terkecil).

    Parameters
    ----------
    df : pd.DataFrame
        Output dari ``process_broksum()``.

    broker_code : str
        Kode broker yang ingin dianalisis (contoh: ``"YU"``, ``"RX"``).
        Case-insensitive — akan dinormalisasi ke UPPERCASE secara otomatis.

    top_n : int
        Jumlah saham maksimum yang ditampilkan di masing-masing tabel
        Top Buy dan Top Sell. Default: 10.

    significance_quantile : float
        Persentil ``|net_value|`` yang digunakan sebagai batas minimum
        "data signifikan". Baris dengan ``|net_value| < threshold`` akan
        disaring. Default: 0.50 (median — hanya tampil separuh teratas).
        Gunakan 0.0 untuk menonaktifkan filter ini.

    date_filter : str | pd.Timestamp | None
        Jika diisi, hanya data pada tanggal tersebut yang diperhitungkan.
        Contoh: ``"2025-03-14"`` atau ``pd.Timestamp("2025-03-14")``.
        Jika None, seluruh periode digabung.

    Returns
    -------
    dict dengan dua kunci:

    ``"top_buy"`` : pd.DataFrame
        Saham dengan net_value terbesar (broker paling banyak beli).
        Kolom: rank, stock_code, buy_value, sell_value, net_value,
               total_value, net_ratio, n_dates.

    ``"top_sell"`` : pd.DataFrame
        Saham dengan net_value terkecil / paling negatif (broker paling
        banyak jual).
        Kolom: rank, stock_code, buy_value, sell_value, net_value,
               total_value, net_ratio, n_dates.

    ``"meta"`` : dict
        Metadata: broker_code, date_filter, n_stocks, significance_threshold.

    Raises
    ------
    ValueError
        Jika df belum diproses atau broker_code tidak ditemukan.
    """
    _check_processed(df)

    # ── 1. Normalisasi & validasi broker_code ────────────────────────────────
    broker_code = str(broker_code).strip().upper()
    available   = df["broker_code"].unique().tolist()
    if broker_code not in available:
        raise ValueError(
            f"Broker '{broker_code}' tidak ditemukan di data.\n"
            f"Contoh broker tersedia: {sorted(available)[:15]}"
        )

    # ── 2. Filter broker ─────────────────────────────────────────────────────
    work = df[df["broker_code"] == broker_code].copy()

    # ── 3. Filter tanggal (opsional) ─────────────────────────────────────────
    if date_filter is not None:
        ts   = pd.Timestamp(date_filter)
        work = work[work["date"].dt.normalize() == ts.normalize()]
        if work.empty:
            raise ValueError(
                f"Broker '{broker_code}' tidak memiliki data pada "
                f"tanggal {date_filter}."
            )

    # ── 4. Agregasi per saham ─────────────────────────────────────────────────
    agg = (
        work.groupby("stock_code", observed=True)
        .agg(
            buy_value  =("buy_value",  "sum"),
            sell_value =("sell_value", "sum"),
            net_value  =("net_value",  "sum"),
            total_value=("total_value","sum"),
            n_dates    =("date",       "nunique"),
        )
        .reset_index()
    )

    # ── 5. Kolom turunan ─────────────────────────────────────────────────────
    agg["net_ratio"] = (
        agg["net_value"] / agg["total_value"].replace(0, float("nan")) * 100
    ).round(2)

    # ── 6. Filter signifikansi ───────────────────────────────────────────────
    significance_threshold = 0.0
    if significance_quantile > 0.0 and len(agg) > 1:
        significance_threshold = float(
            agg["net_value"].abs().quantile(significance_quantile)
        )
        agg = agg[agg["net_value"].abs() >= significance_threshold].copy()

    # ── 7. Top Buy — net terbesar (positif) ───────────────────────────────────
    top_buy = (
        agg[agg["net_value"] > 0]
        .sort_values("net_value", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    top_buy.insert(0, "rank", range(1, len(top_buy) + 1))

    # ── 8. Top Sell — net terkecil (paling negatif) ───────────────────────────
    top_sell = (
        agg[agg["net_value"] < 0]
        .sort_values("net_value", ascending=True)   # paling negatif dulu
        .head(top_n)
        .reset_index(drop=True)
    )
    top_sell.insert(0, "rank", range(1, len(top_sell) + 1))

    # ── 9. Urutkan kolom output ───────────────────────────────────────────────
    _out_cols = [
        "rank", "stock_code",
        "buy_value", "sell_value",
        "net_value", "total_value",
        "net_ratio", "n_dates",
    ]
    top_buy  = top_buy[_out_cols]
    top_sell = top_sell[_out_cols]

    # ── 10. Tipe akhir ────────────────────────────────────────────────────────
    _int_cols = ["buy_value", "sell_value", "net_value", "total_value"]
    for _tbl in (top_buy, top_sell):
        _tbl[_int_cols] = _tbl[_int_cols].astype("int64")

    return {
        "top_buy":  top_buy,
        "top_sell": top_sell,
        "meta": {
            "broker_code":            broker_code,
            "date_filter":            str(date_filter) if date_filter else "Semua",
            "n_stocks_after_filter":  len(agg),
            "significance_threshold": significance_threshold,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# STOCK ACTIVITY  —  analisis 1 saham
# ─────────────────────────────────────────────────────────────────────────────

def stock_activity(
    df: pd.DataFrame,
    stock_code: str,
    top_n: int = 10,
    date_filter: "str | pd.Timestamp | None" = None,
) -> dict:
    """
    Tampilkan aktivitas untuk saham tertentu, meliputi:
    Top broker net buy, Top broker net sell, dan total net_value.

    Parameters
    ----------
    df : pd.DataFrame
        Output dari ``process_broksum()``.
    stock_code : str
        Kode saham yang ingin dianalisis (contoh: ``"BBCA"``).
    top_n : int
        Jumlah broker maksimum yang ditampilkan.
    date_filter : str | pd.Timestamp | None
        Filter tanggal (opsional).

    Returns
    -------
    dict dengan kunci:
        "top_buy": pd.DataFrame,
        "top_sell": pd.DataFrame,
        "summary": dict (total_buy, total_sell, net_value, signal)
    """
    _check_processed(df)

    stock_code = str(stock_code).strip().upper()
    available = df["stock_code"].unique().tolist()
    if stock_code not in available:
        raise ValueError(
            f"Saham '{stock_code}' tidak ditemukan di data.\n"
            f"Contoh saham tersedia: {sorted(available)[:15]}"
        )

    work = df[df["stock_code"] == stock_code].copy()

    if date_filter is not None:
        ts = pd.Timestamp(date_filter)
        work = work[work["date"].dt.normalize() == ts.normalize()]
        if work.empty:
            raise ValueError(
                f"Saham '{stock_code}' tidak memiliki data pada tanggal {date_filter}."
            )

    # Agregasi per broker
    agg = (
        work.groupby("broker_code", observed=True)
        .agg(
            buy_value  =("buy_value",  "sum"),
            sell_value =("sell_value", "sum"),
            net_value  =("net_value",  "sum"),
            total_value=("total_value","sum"),
        )
        .reset_index()
    )

    agg["net_ratio"] = (
        agg["net_value"] / agg["total_value"].replace(0, float("nan")) * 100
    ).round(2)

    top_buy = (
        agg[agg["net_value"] > 0]
        .sort_values("net_value", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    top_buy.insert(0, "rank", range(1, len(top_buy) + 1))

    top_sell = (
        agg[agg["net_value"] < 0]
        .sort_values("net_value", ascending=True)
        .head(top_n)
        .reset_index(drop=True)
    )
    top_sell.insert(0, "rank", range(1, len(top_sell) + 1))

    total_buy = agg["buy_value"].sum()
    total_sell = agg["sell_value"].sum()
    total_net = total_buy - total_sell

    # Signal Logic
    cross_count = work["is_cross"].sum()
    
    # Simple heuristic
    if cross_count > len(work) * 0.3:  # Jika > 30% transaksi adalah cross
        signal = "Cross / Neutral"
    elif total_net > 0:
        signal = "Akumulasi"
    elif total_net < 0:
        signal = "Distribusi"
    else:
        signal = "Neutral"

    return {
        "top_buy": top_buy,
        "top_sell": top_sell,
        "summary": {
            "total_buy": total_buy,
            "total_sell": total_sell,
            "total_net": total_net,
            "signal": signal,
            "cross_count": cross_count
        }
    }


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
# MARKET OVERVIEW  —  tabel aktivitas broker secara global
# ─────────────────────────────────────────────────────────────────────────────

def market_overview(
    df: pd.DataFrame,
    date_filter: "str | pd.Timestamp | None" = None,
    top_n: int | None = None,
) -> pd.DataFrame:
    """
    Hasilkan tabel Market Overview: aktivitas broker secara global,
    diurutkan berdasarkan total_value (terbesar dulu).

    Parameters
    ----------
    df : pd.DataFrame
        Output dari ``process_broksum()``.

    date_filter : str | pd.Timestamp | None
        Jika diisi, hanya baris dengan tanggal tersebut yang dihitung.
        Contoh: "2025-01-10"  atau  pd.Timestamp("2025-01-10")
        Jika None (default), semua tanggal digabung.

    top_n : int | None
        Jika diisi, kembalikan hanya top-N broker berdasarkan total_value.
        Jika None, kembalikan semua broker.

    Returns
    -------
    pd.DataFrame dengan kolom:
        rank          – peringkat berdasarkan total_value (1 = terbesar)
        broker_code   – kode broker
        total_buy     – total nilai beli (Rupiah)
        total_sell    – total nilai jual (Rupiah)
        net_value     – total_buy - total_sell
        total_value   – total_buy + total_sell
        net_ratio     – net_value / total_value  (dalam %, -100 s/d +100)
        buy_pct       – total_buy / total_value  (proporsi beli)
        cross_count   – jumlah baris cross-trade yang melibatkan broker ini
        stocks_traded – jumlah kode saham berbeda yang ditransaksikan
        status        – "Net Buy" | "Net Sell"

    Raises
    ------
    ValueError
        Jika df belum diproses oleh process_broksum().
    """
    _check_processed(df)

    # ── 1. Filter tanggal (opsional) ─────────────────────────────────────────
    work = df.copy()
    if date_filter is not None:
        ts = pd.Timestamp(date_filter)
        work = work[work["date"].dt.normalize() == ts.normalize()]
        if work.empty:
            raise ValueError(
                f"Tidak ada data untuk tanggal: {date_filter}. "
                f"Tanggal tersedia: {sorted(df['date'].dt.date.unique())}"
            )

    # ── 2. Group by broker_code ───────────────────────────────────────────────
    grp = work.groupby("broker_code", observed=True)

    overview = grp.agg(
        total_buy    =("buy_value",   "sum"),
        total_sell   =("sell_value",  "sum"),
        net_value    =("net_value",   "sum"),
        total_value  =("total_value", "sum"),
        cross_count  =("is_cross",    "sum"),
        stocks_traded=("stock_code",  "nunique"),
    ).reset_index()

    # ── 3. Kolom turunan ─────────────────────────────────────────────────────
    # net_ratio: seberapa condong broker ke beli (+) atau jual (-), dalam %
    overview["net_ratio"] = (
        overview["net_value"] / overview["total_value"].replace(0, float("nan")) * 100
    ).round(2)

    # buy_pct: proporsi nilai beli terhadap total transaksi broker
    overview["buy_pct"] = (
        overview["total_buy"] / overview["total_value"].replace(0, float("nan")) * 100
    ).round(2)

    # ── 4. Status label ───────────────────────────────────────────────────────
    overview["status"] = overview["net_value"].apply(
        lambda v: "Net Buy" if v >= 0 else "Net Sell"
    )

    # ── 5. Sort by total_value DESC ───────────────────────────────────────────
    overview = overview.sort_values("total_value", ascending=False, ignore_index=True)

    # ── 6. Rank (setelah sort) ────────────────────────────────────────────────
    overview.insert(0, "rank", range(1, len(overview) + 1))

    # ── 7. Pilih & urutkan kolom output ──────────────────────────────────────
    col_order = [
        "rank", "broker_code",
        "total_buy", "total_sell",
        "net_value", "total_value",
        "net_ratio", "buy_pct",
        "cross_count", "stocks_traded",
        "status",
    ]
    overview = overview[col_order]

    # ── 8. Top-N (opsional) ───────────────────────────────────────────────────
    if top_n is not None:
        overview = overview.head(int(top_n)).reset_index(drop=True)
        overview["rank"] = range(1, len(overview) + 1)  # re-rank setelah slice

    # ── 9. Tipe akhir ─────────────────────────────────────────────────────────
    int_cols = ["total_buy", "total_sell", "net_value", "total_value", "cross_count"]
    overview[int_cols] = overview[int_cols].astype("int64")
    overview["status"] = overview["status"].astype("category")

    return overview


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
    # ── Market Overview demo ─────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("MARKET OVERVIEW  (semua tanggal, semua broker)")
    print("=" * 70)
    ov_all = market_overview(processed)
    print(ov_all.to_string(index=False))

    print("\n" + "=" * 70)
    print("MARKET OVERVIEW  (tanggal spesifik: 2025-01-02, top 5)")
    print("==" * 35)
    ov_date = market_overview(processed, date_filter="2025-01-02", top_n=5)
    print(ov_date.to_string(index=False))


# ─────────────────────────────────────────────────────────────────────────────
# CONTOH INTEGRASI STREAMLIT
# ─────────────────────────────────────────────────────────────────────────────
#
# import streamlit as st
# from broksum_processor import process_broksum, market_overview
#
# @st.cache_data(ttl=300)
# def load_overview(df_raw, date_sel=None, top_n=None):
#     processed = process_broksum(df_raw)
#     return market_overview(processed, date_filter=date_sel, top_n=top_n)
#
# def render_market_overview(df_raw):
#     st.subheader("Market Overview -- Aktivitas Broker Global")
#
#     col_date, col_top = st.columns([2, 1])
#     with col_date:
#         dates = sorted(df_raw["date"].dt.date.unique(), reverse=True)
#         sel_date = st.selectbox("Filter Tanggal", ["Semua"] + [str(d) for d in dates])
#     with col_top:
#         top_n = st.number_input("Top-N Broker", min_value=3, max_value=50, value=20)
#
#     date_filter = None if sel_date == "Semua" else sel_date
#     ov = load_overview(df_raw, date_sel=date_filter, top_n=top_n)
#
#     def color_status(val):
#         color = "#22c55e" if val == "Net Buy" else "#ef4444"
#         return f"color: {color}; font-weight: 700"
#
#     st.dataframe(
#         ov.style.map(color_status, subset=["status"]),
#         use_container_width=True,
#         hide_index=True,
#         column_config={
#             "rank":          st.column_config.NumberColumn("#",         width="small"),
#             "broker_code":   st.column_config.TextColumn("Broker",      width="small"),
#             "total_buy":     st.column_config.NumberColumn("Total Buy",  format="Rp%,.0f"),
#             "total_sell":    st.column_config.NumberColumn("Total Sell", format="Rp%,.0f"),
#             "net_value":     st.column_config.NumberColumn("Net Value",  format="Rp%,.0f"),
#             "total_value":   st.column_config.NumberColumn("Total",      format="Rp%,.0f"),
#             "net_ratio":     st.column_config.NumberColumn("Net %",      format="%.2f%%"),
#             "buy_pct":       st.column_config.NumberColumn("Buy %",      format="%.2f%%"),
#             "cross_count":   st.column_config.NumberColumn("Cross",      width="small"),
#             "stocks_traded": st.column_config.NumberColumn("Saham",      width="small"),
#             "status":        st.column_config.TextColumn("Status"),
#         },
#     )
