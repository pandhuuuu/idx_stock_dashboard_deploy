import pandas as pd
import numpy as np

def analyze_volume(high: np.ndarray, low: np.ndarray, close: np.ndarray, open_: np.ndarray, volume: np.ndarray):
    vol_ma = pd.Series(volume).rolling(20).mean().values
    
    volume_spike = volume[-1] > 2 * vol_ma[-1] if not np.isnan(vol_ma[-1]) else False
    extreme_volume = volume[-1] > 3.5 * vol_ma[-1] if not np.isnan(vol_ma[-1]) else False
    
    bullish_candle = close[-1] > open_[-1]
    bearish_candle = close[-1] < open_[-1]
    
    bandar_masuk = volume_spike and bullish_candle
    bandar_keluar = volume_spike and bearish_candle
    
    extreme_buy = extreme_volume and bullish_candle
    extreme_sell = extreme_volume and bearish_candle
    
    body = abs(close[-1] - open_[-1])
    candle_range = max(high[-1] - low[-1], 1e-6)
    battle_zone = (body / candle_range < 0.3) and volume_spike
    
    return {
        "bandar_masuk": bandar_masuk,
        "bandar_keluar": bandar_keluar,
        "battle_zone": battle_zone,
        "volume_spike": volume_spike,
        "extreme": extreme_volume,
        "extreme_buy": extreme_buy,
        "extreme_sell": extreme_sell
    }
