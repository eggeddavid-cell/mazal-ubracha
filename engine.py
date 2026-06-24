import math
import pandas as pd
from data import get_market_data
from indicators import add_indicators, detect_levels, detect_patterns

def _safe(row, key, default=0):
    try:
        v = row.get(key, default)
        if pd.isna(v):
            return default
        return v
    except Exception:
        return default

def _components(row):
    close = _safe(row, "Close")
    ema20 = _safe(row, "EMA20", close)
    ema50 = _safe(row, "EMA50", close)
    ema200 = _safe(row, "EMA200", close)
    adx = _safe(row, "ADX")
    rsi = _safe(row, "RSI", 50)
    macd_hist = _safe(row, "MACD_Hist")
    stoch_k = _safe(row, "Stoch_K", 50)
    stoch_d = _safe(row, "Stoch_D", 50)
    volume_ratio = _safe(row, "Volume_Ratio", 1)
    obv = _safe(row, "OBV")
    obv_ema = _safe(row, "OBV_EMA")
    atr = _safe(row, "ATR")
    atr_ma = _safe(row, "ATR_MA", atr)
    bb_upper = _safe(row, "BB_Upper", close * 999)
    bb_lower = _safe(row, "BB_Lower", close * -999)
    vwap = _safe(row, "VWAP", close)
    ret5 = _safe(row, "Return_5")

    trend = 0
    trend += 5 if close > ema20 else 0
    trend += 5 if ema20 > ema50 else 0
    trend += 8 if ema50 > ema200 else 0
    trend += 7 if adx > 22 else 0

    momentum = 0
    momentum += 8 if rsi > 50 else 0
    momentum += 6 if macd_hist > 0 else 0
    momentum += 6 if stoch_k > stoch_d else 0

    volume = 0
    volume += 10 if volume_ratio > 1.2 else 5 if volume_ratio > 1 else 0
    volume += 5 if obv > obv_ema else 0

    volatility = 0
    volatility += 8 if atr > atr_ma else 0
    volatility += 7 if close > bb_upper or close < bb_lower else 3

    price_action = 0
    price_action += 8 if close > vwap else 0
    price_action += 7 if ret5 > 0 else 0

    return {
        "Trend": trend,
        "Momentum": momentum,
        "Volume": volume,
        "Volatility": volatility,
        "Price Action": price_action,
    }

def _direction_score(row):
    close = _safe(row, "Close")
    score = 50
    checks = []

    def add(name, cond, w):
        nonlocal score
        score += w if cond else -w
        checks.append({"בדיקה": name, "תוצאה": "חיובי" if cond else "שלילי", "משקל": w})

    add("מחיר מעל VWAP", close > _safe(row, "VWAP", close), 9)
    add("EMA20 מעל EMA50", _safe(row, "EMA20", close) > _safe(row, "EMA50", close), 8)
    add("מחיר מעל EMA200", close > _safe(row, "EMA200", close), 7)
    add("MACD חיובי", _safe(row, "MACD_Hist") > 0, 7)
    add("RSI מעל 50", _safe(row, "RSI", 50) > 50, 6)
    add("+DI מעל -DI", _safe(row, "Plus_DI") > _safe(row, "Minus_DI"), 5)
    add("Volume מעל ממוצע", _safe(row, "Volume_Ratio", 1) > 1, 6)
    add("OBV מעל ממוצע", _safe(row, "OBV") > _safe(row, "OBV_EMA"), 5)
    add("תשואה 5 נרות חיובית", _safe(row, "Return_5") > 0, 5)
    return max(0, min(100, int(score))), checks

def _risk_label(rr, vol_ratio):
    if rr >= 2.2 and vol_ratio < 2.5:
        return "LOW"
    if rr >= 1.5:
        return "MEDIUM"
    return "HIGH"

def run_backtest(df, horizon=8):
    trades = []
    if len(df) < 80:
        return {"עסקאות במדגם": 0, "אחוז הצלחה": None, "תוחלת R": None}, []

    for i in range(60, len(df) - horizon - 1):
        score, _ = _direction_score(df.iloc[i])
        action = "CALL" if score >= 68 else "PUT" if score <= 35 else "WAIT"
        if action == "WAIT":
            continue

        entry = float(_safe(df.iloc[i], "Close"))
        atr = float(_safe(df.iloc[i], "ATR", entry * 0.01))
        future = df.iloc[i + 1:i + 1 + horizon]

        if action == "CALL":
            win = 0 if any(future["Low"] <= entry - 1.1 * atr) else int(any(future["High"] >= entry + 1.5 * atr))
        else:
            win = 0 if any(future["High"] >= entry + 1.1 * atr) else int(any(future["Low"] <= entry - 1.5 * atr))

        trades.append({"זמן": str(df.index[i]), "פעולה": action, "ציון": score, "תוצאה": "ניצחון" if win else "הפסד", "win": win})

    if not trades:
        return {"עסקאות במדגם": 0, "אחוז הצלחה": None, "תוחלת R": None}, []

    h = pd.DataFrame(trades)
    wr = float(h["win"].mean() * 100)
    exp = (wr / 100) * 1.5 - (1 - wr / 100) * 1.1
    return {"עסקאות במדגם": len(trades), "אחוז הצלחה": round(wr, 1), "תוחלת R": round(exp, 3)}, trades

def analyze_symbol(symbol, df, levels, patterns, tf_data, horizon, account_size, risk_pct):
    last = df.iloc[-1]
    direction_score, checks = _direction_score(last)
    components = _components(last)
    raw_quality = sum(components.values())

    bt, trades = run_backtest(df, horizon)
    sample, wr = bt.get("עסקאות במדגם", 0), bt.get("אחוז הצלחה")

    mtf = []
    mtf_score = 0
    for name, tdf in tf_data.items():
        try:
            s, _ = _direction_score(tdf.iloc[-1])
            d = "CALL" if s >= 65 else "PUT" if s <= 38 else "WAIT"
            mtf.append({"טיים פריים": name, "כיוון": d, "ציון": s})
            mtf_score += 5 if d == "CALL" else -5 if d == "PUT" else 0
        except Exception:
            pass

    pattern_text = " ".join([p.get("כיוון", "") for p in patterns])
    pattern_bonus = 4 if "שורית" in pattern_text else -4 if "דובית" in pattern_text else 0

    call_prob = 100 / (1 + math.exp(-(direction_score - 50) / 10))
    call_prob += mtf_score + pattern_bonus

    if wr is not None and sample >= 10:
        w = min(0.35, sample / 100)
        call_prob = call_prob * (1 - w) + (wr if direction_score >= 50 else 100 - wr) * w

    call_prob = round(max(5, min(95, call_prob)), 1)
    put_prob = round(max(5, min(95, 100 - call_prob)), 1)
    wait_prob = round(max(0, 100 - max(call_prob, put_prob)), 1)

    action = "STRONG CALL" if call_prob >= 78 else "CALL" if call_prob >= 63 else "STRONG PUT" if put_prob >= 78 else "PUT" if put_prob >= 63 else "WAIT"

    quality_score = int(max(0, min(100, raw_quality + (10 if sample >= 10 and wr and wr > 55 else 0) + abs(mtf_score))))
    confidence = int(max(35, min(95, 45 + min(20, sample * 0.4) + (10 if abs(call_prob - 50) >= 15 else 0) + (10 if quality_score >= 75 else 0))))
    grade = "A+" if quality_score >= 88 and confidence >= 75 else "A" if quality_score >= 78 else "B" if quality_score >= 68 else "C" if quality_score >= 55 else "D"

    entry = float(_safe(last, "Close"))
    atr = float(_safe(last, "ATR", entry * 0.01))
    support, resistance = float(levels["support"]), float(levels["resistance"])

    if "CALL" in action:
        stop, t1, t2 = max(support, entry - 1.1 * atr), entry + 1.5 * atr, entry + 2.4 * atr
    elif "PUT" in action:
        stop, t1, t2 = min(resistance, entry + 1.1 * atr), entry - 1.5 * atr, entry - 2.4 * atr
    else:
        stop, t1, t2 = support, resistance, resistance + atr

    unit_r = abs(entry - stop)
    rr = abs(t1 - entry) / unit_r if unit_r else 0
    risk_d = account_size * risk_pct / 100
    units = int(risk_d / unit_r) if unit_r > 0 else 0
    risk_label = _risk_label(rr, float(_safe(last, "Volume_Ratio", 1)))

    trade_plan = {
        "פעולה": action, "Grade": grade, "כניסה": round(entry, 2), "סטופ": round(stop, 2),
        "יעד 1": round(t1, 2), "יעד 2": round(t2, 2), "יחס סיכון/סיכוי": round(rr, 2),
        "CALL %": call_prob, "PUT %": put_prob, "WAIT %": wait_prob, "Risk": risk_label
    }

    risk_plan = {
        "גודל חשבון": account_size, "סיכון %": risk_pct, "סיכון $": round(risk_d, 2),
        "סיכון ליחידה": round(unit_r, 2), "כמות יחידות": units, "ATR": round(atr, 3), "Risk": risk_label
    }

    latest = {
        "Close": round(entry, 2), "VWAP": round(float(_safe(last, "VWAP", entry)), 2),
        "EMA20": round(float(_safe(last, "EMA20", entry)), 2), "EMA50": round(float(_safe(last, "EMA50", entry)), 2),
        "EMA200": round(float(_safe(last, "EMA200", entry)), 2), "RSI": round(float(_safe(last, "RSI", 50)), 2),
        "MACD Hist": round(float(_safe(last, "MACD_Hist")), 4), "ADX": round(float(_safe(last, "ADX")), 2),
        "Volume Ratio": round(float(_safe(last, "Volume_Ratio", 1)), 2), "ATR": round(atr, 3)
    }

    flow_analysis = {
        "Trend": components["Trend"], "Momentum": components["Momentum"], "Volume": components["Volume"],
        "Volatility": components["Volatility"], "Price Action": components["Price Action"],
        "Multi TF Bonus": mtf_score, "Pattern Bonus": pattern_bonus,
        "Quality Score": quality_score, "Setup Grade": grade
    }

    score_breakdown = [{"רכיב": k, "ציון": v} for k, v in components.items()]
    score_breakdown += [{"רכיב": "Multi-Timeframe", "ציון": mtf_score}, {"רכיב": "Pattern", "ציון": pattern_bonus}, {"רכיב": "Quality Total", "ציון": quality_score}]

    summary = f"{symbol}: {action}, Grade {grade}, איכות {quality_score}/100, CALL {call_prob}%, PUT {put_prob}%, אמינות {confidence}%. Risk {risk_label}. Backtest: {sample} עסקאות, הצלחה {wr}%."

    return {
        "action": action, "grade": grade, "call_prob": call_prob, "put_prob": put_prob, "wait_prob": wait_prob,
        "confidence": confidence, "quality_score": quality_score, "risk_label": risk_label, "last_close": entry,
        "summary": summary, "trade_plan": trade_plan, "risk_plan": risk_plan, "latest_indicators": latest,
        "score_breakdown": score_breakdown, "multi_timeframe": mtf, "backtest_summary": bt, "backtest_trades": trades,
        "flow_analysis": flow_analysis
    }

def scan_symbols(symbols, interval="15min", horizon=8):
    rows = []
    for sym in symbols:
        try:
            df, source, err = get_market_data(sym, interval=interval)
            if err or df.empty:
                continue
            df = add_indicators(df)
            if len(df) < 80:
                continue
            levels = detect_levels(df)
            patterns = detect_patterns(df)
            res = analyze_symbol(sym, df, levels, patterns, {}, horizon, 10000, 1)
            rows.append({
                "סימול": sym,
                "פעולה": res["action"],
                "Grade": res["grade"],
                "ציון איכות": res["quality_score"],
                "CALL %": res["call_prob"],
                "PUT %": res["put_prob"],
                "Risk": res["risk_label"],
                "מחיר": round(res["last_close"], 2),
                "מקור": source
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    grade_rank = {"A+": 5, "A": 4, "B": 3, "C": 2, "D": 1}
    df["_rank"] = df["Grade"].map(grade_rank).fillna(0)
    return df.sort_values(["_rank", "ציון איכות"], ascending=False).drop(columns=["_rank"])
