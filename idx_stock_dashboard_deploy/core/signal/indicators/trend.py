import talib
import numpy as np

def get_dmi(high: np.ndarray, low: np.ndarray, close: np.ndarray, timeperiod=14):
    plus_di  = talib.PLUS_DI(high, low, close, timeperiod=timeperiod)
    minus_di = talib.MINUS_DI(high, low, close, timeperiod=timeperiod)
    adx_arr  = talib.ADX(high, low, close, timeperiod=timeperiod)
    
    adx_val  = float(adx_arr[-1]) if not np.isnan(adx_arr[-1]) else 0.0
    pdi      = float(plus_di[-1])  if not np.isnan(plus_di[-1])  else 0.0
    mdi      = float(minus_di[-1]) if not np.isnan(minus_di[-1]) else 0.0
    
    trend_strong = adx_val > 25
    dmi_bull  = bool(pdi > mdi and trend_strong)
    dmi_bear  = bool(mdi > pdi and trend_strong)
    
    return {
        "adx_val": adx_val,
        "pdi": pdi,
        "mdi": mdi,
        "trend_strong": trend_strong,
        "dmi_bull": dmi_bull,
        "dmi_bear": dmi_bear
    }

def get_sma_cross(close: np.ndarray, short_period=10, long_period=30):
    import pandas as pd
    sma_s = pd.Series(close).rolling(short_period).mean().values
    sma_l = pd.Series(close).rolling(long_period).mean().values
    sma_bull = bool(sma_s[-1] > sma_l[-1])
    return sma_bull
