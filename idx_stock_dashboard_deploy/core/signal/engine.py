import pandas as pd

from core.signal.indicators.trend import get_dmi, get_sma_cross
from core.signal.indicators.momentum import get_rsi, get_macd, get_kst_signal
from core.signal.indicators.volume import analyze_volume
from core.signal.indicators.volatility import get_atr_sl_tp
from core.signal.scoring import calculate_score

def calculate_signals(df: pd.DataFrame) -> dict:
    high  = df["High"].values.astype(float)
    low   = df["Low"].values.astype(float)
    close = df["Close"].values.astype(float)
    open_ = df["Open"].values.astype(float)
    volume = df["Volume"].values.astype(float)

    if len(close) < 35:
        return None

    price_now = float(close[-1])

    vol_ind = analyze_volume(high, low, close, open_, volume)
    sma_bull = get_sma_cross(close)
    rsi_val = get_rsi(close)
    macd_ind = get_macd(close)
    dmi_ind = get_dmi(high, low, close)
    kst_ind = get_kst_signal(close)
    atr_ind = get_atr_sl_tp(high, low, close, price_now)

    ind_dict = {
        **vol_ind,
        **macd_ind,
        **kst_ind,
        "sma_bull": sma_bull,
        "rsi": rsi_val,
        "dmi_bull": dmi_ind["dmi_bull"],
        "dmi_bear": dmi_ind["dmi_bear"],
        "trend_strong": dmi_ind["trend_strong"],
    }

    bull_score, bear_score, confidence, signal = calculate_score(ind_dict)

    return {
        "price":         price_now,
        "rsi":           round(rsi_val, 2),
        "bull_score":    bull_score,
        "bear_score":    bear_score,
        "confidence":    confidence,
        "suggested_sl":  round(atr_ind["suggested_sl"], 2),
        "suggested_tp":  round(atr_ind["suggested_tp"], 2),
        "risk_reward":   round(atr_ind["risk_reward"], 2),
        
        "bandar_masuk":  vol_ind["bandar_masuk"],
        "bandar_keluar": vol_ind["bandar_keluar"],
        "battle_zone":   vol_ind["battle_zone"],
        "volume_spike":  vol_ind["volume_spike"],
        "extreme":       vol_ind["extreme"],
        
        "signal":        signal,
        "adx":           round(dmi_ind["adx_val"], 2),
        "plus_di":       round(dmi_ind["pdi"], 2),
        "minus_di":      round(dmi_ind["mdi"], 2),
        "kst":           round(kst_ind["kst_val"], 4),
        "kst_signal":    round(kst_ind["kst_s"], 4),
        "macd_cross":    "↑" if macd_ind["macd_cross_up"] else ("↓" if macd_ind["macd_cross_down"] else "-"),
        "kst_cross":     "↑" if kst_ind["kst_cross_up"]  else ("↓" if kst_ind["kst_cross_down"]  else "-"),
    }
