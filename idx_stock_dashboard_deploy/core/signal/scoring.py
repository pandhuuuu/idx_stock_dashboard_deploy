def calculate_score(ind: dict) -> tuple[float, float, float, str]:
    bull_score = 0.0
    bear_score = 0.0

    # ── SMA ──
    if ind['sma_bull'] and ind['trend_strong']:
        bull_score += 1
    elif not ind['sma_bull'] and ind['trend_strong']:
        bear_score += 1

    # ── RSI ──
    if ind['rsi'] < 30:
        bull_score += 2
    elif ind['rsi'] > 70:
        bear_score += 2

    # ── MACD ──
    if ind['macd_cross_up']:
        bull_score += 2
    elif ind['macd_cross_down']:
        bear_score += 2
    elif ind['macd_bull']:
        bull_score += 1
    else:
        bear_score += 1

    # ── DMI ──
    if ind['dmi_bull']:
        bull_score += 2
    elif ind['dmi_bear']:
        bear_score += 2

    # ── KST ──
    if ind['kst_cross_up']:
        bull_score += 1
    elif ind['kst_cross_down']:
        bear_score += 1
    elif ind['kst_bull']:
        bull_score += 0.5
    else:
        bear_score += 0.5
        
    # ── BANDARMOLOGY ──
    if ind['volume_spike']:
        bull_score += 1
    if ind['bandar_masuk']:
        bull_score += 2
    if ind['bandar_keluar']:
        bear_score += 2
    if ind['extreme_buy']:
        bull_score += 3
    if ind['extreme_sell']:
        bear_score += 3
    if ind['battle_zone']:
        bull_score += 0.5
        bear_score += 0.5

    bull_score = round(bull_score, 1)
    bear_score = round(bear_score, 1)
    
    total_max  = bull_score + bear_score
    confidence = round(max(bull_score, bear_score) / total_max * 100, 1) if total_max else 50.0

    margin = bull_score - bear_score
    if margin >= 2:
        signal = "BUY"
    elif margin <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    return bull_score, bear_score, confidence, signal
