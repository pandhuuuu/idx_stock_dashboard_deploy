import talib
import numpy as np
import pandas as pd

def get_rsi(close: np.ndarray, timeperiod=14):
    rsi_arr = talib.RSI(close, timeperiod=timeperiod)
    rsi_val = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0
    return rsi_val

def get_macd(close: np.ndarray):
    macd_line, macd_sig, macd_hist = talib.MACD(close)
    if (not np.isnan(macd_line[-2]) and not np.isnan(macd_sig[-2]) and
            not np.isnan(macd_line[-1]) and not np.isnan(macd_sig[-1])):
        macd_cross_up   = (macd_line[-2] < macd_sig[-2]) and (macd_line[-1] > macd_sig[-1])
        macd_cross_down = (macd_line[-2] > macd_sig[-2]) and (macd_line[-1] < macd_sig[-1])
        macd_bull       = macd_line[-1] > macd_sig[-1]
    else:
        macd_cross_up = macd_cross_down = False
        macd_bull = False
        
    return {
        "macd_cross_up": macd_cross_up,
        "macd_cross_down": macd_cross_down,
        "macd_bull": macd_bull
    }

def _sma(series: np.ndarray, period: int) -> np.ndarray:
    return pd.Series(series).rolling(period).mean().values

def calculate_kst(close: np.ndarray):
    roc10 = talib.ROC(close, timeperiod=10)
    roc15 = talib.ROC(close, timeperiod=15)
    roc20 = talib.ROC(close, timeperiod=20)
    roc30 = talib.ROC(close, timeperiod=30)

    kst = (
        _sma(roc10, 10) * 1 +
        _sma(roc15, 10) * 2 +
        _sma(roc20, 10) * 3 +
        _sma(roc30, 15) * 4
    )
    signal = _sma(kst, 9)
    return kst, signal

def get_kst_signal(close: np.ndarray):
    kst_arr, kst_sig_arr = calculate_kst(close)
    kst_val  = float(kst_arr[-1])     if not np.isnan(kst_arr[-1])     else 0.0
    kst_s    = float(kst_sig_arr[-1]) if not np.isnan(kst_sig_arr[-1]) else 0.0
    kst_prev = float(kst_arr[-2])     if not np.isnan(kst_arr[-2])     else kst_val
    kst_s_p  = float(kst_sig_arr[-2]) if not np.isnan(kst_sig_arr[-2]) else kst_s
    
    kst_cross_up   = (kst_prev < kst_s_p) and (kst_val > kst_s)
    kst_cross_down = (kst_prev > kst_s_p) and (kst_val < kst_s)
    kst_bull = kst_val > kst_s and kst_val > 0
    
    return {
        "kst_val": kst_val,
        "kst_s": kst_s,
        "kst_cross_up": kst_cross_up,
        "kst_cross_down": kst_cross_down,
        "kst_bull": kst_bull
    }
