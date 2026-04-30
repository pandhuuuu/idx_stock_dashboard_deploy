import talib
import numpy as np

def get_atr_sl_tp(high: np.ndarray, low: np.ndarray, close: np.ndarray, price_now: float, timeperiod=14):
    atr_arr = talib.ATR(high, low, close, timeperiod=timeperiod)
    atr_val = float(atr_arr[-1]) if not np.isnan(atr_arr[-1]) else price_now * 0.02
    
    suggested_sl = price_now - 1.5 * atr_val
    suggested_tp = price_now + 2.5 * atr_val
    risk_reward  = abs(suggested_tp - price_now) / max(abs(price_now - suggested_sl), 1e-6)
    
    return {
        "atr_val": atr_val,
        "suggested_sl": suggested_sl,
        "suggested_tp": suggested_tp,
        "risk_reward": risk_reward
    }
