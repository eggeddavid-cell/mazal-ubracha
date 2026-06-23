def _add(checks, name, condition, weight, score):
    score += weight if condition else -weight
    checks.append({"בדיקה": name, "תוצאה": "חיובי" if condition else "שלילי", "משקל": weight})
    return score

def build_report(symbol, df, levels, options, news_items, patterns, account_size, risk_pct):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    score = 50
    checks = []

    score = _add(checks, "מחיר מעל VWAP", last["Close"] > last["VWAP"], 10, score)
    score = _add(checks, "EMA20 מעל EMA50", last["EMA20"] > last["EMA50"], 8, score)
    score = _add(checks, "מחיר מעל EMA200", last["Close"] > last["EMA200"], 7, score)
    score = _add(checks, "MACD מעל Signal", last["MACD"] > last["MACD_Signal"], 8, score)
    score = _add(checks, "RSI מעל 50", last["RSI"] > 50, 6, score)
    score = _add(checks, "RSI לא בקיצון", 25 < last["RSI"] < 75, 5, score)
    score = _add(checks, "Volume מעל ממוצע", last["Volume_Ratio"] > 1, 7, score)
    score = _add(checks, "סגירה עולה מול נר קודם", last["Close"] > prev["Close"], 5, score)

    pcr = options.get("put_call_volume_ratio")
    if pcr is not None:
        score = _add(checks, "Put/Call Ratio תומך", pcr < 0.9, 8, score)

    max_pain = options.get("max_pain")
    if max_pain:
        score = _add(checks, "מחיר מעל Max Pain", last["Close"] > max_pain, 5, score)

    gex = options.get("gex_bias")
    if gex and "חיובי" in str(gex):
        score += 4
        checks.append({"בדיקה": "GEX חיובי", "תוצאה": "חיובי", "משקל": 4})
    elif gex and "שלילי" in str(gex):
        score -= 4
        checks.append({"בדיקה": "GEX שלילי", "תוצאה": "שלילי", "משקל": 4})

    names = " ".join([p.get("תבנית","") for p in patterns])
    if "פטיש" in names or "Bullish" in names:
        score += 5
        checks.append({"בדיקה": "תבנית נרות שורית", "תוצאה": "חיובי", "משקל": 5})
    if "כוכב נופל" in names or "Bearish" in names:
        score -= 5
        checks.append({"בדיקה": "תבנית נרות דובית", "תוצאה": "שלילי", "משקל": 5})

    score = max(0, min(100, int(score)))
    trend = "שורית" if score >= 68 else "דובית" if score <= 35 else "ניטרלית"
    action = "CALL" if trend == "שורית" and score >= 72 else "PUT" if trend == "דובית" and score <= 30 else "WAIT"

    confidence = 55
    if options.get("source") in ["tradier", "polygon"]:
        confidence += 25
    elif options.get("source") == "yahoo_limited":
        confidence += 10
    if len(df) >= 80:
        confidence += 10
    if abs(score - 50) >= 20:
        confidence += 10
    confidence = min(95, confidence)

    risk = "גבוה" if last["RSI"] > 75 or last["Volume_Ratio"] > 3 else "בינוני"
    atr = float(last.get("ATR", 0) or 0)
    entry = float(last["Close"])
    support = float(levels["support"])
    resistance = float(levels["resistance"])

    if action == "CALL":
        stop = max(support, entry - atr * 1.2)
        target1 = entry + atr * 1.5
        target2 = entry + atr * 2.5
    elif action == "PUT":
        stop = min(resistance, entry + atr * 1.2)
        target1 = entry - atr * 1.5
        target2 = entry - atr * 2.5
    else:
        stop = support
        target1 = resistance
        target2 = resistance + atr

    risk_dollars = account_size * (risk_pct / 100)
    per_share_risk = abs(entry - stop)
    shares = int(risk_dollars / per_share_risk) if per_share_risk else 0

    trade_plan = {
        "פעולה": action,
        "כיוון": trend,
        "כניסה": round(entry, 2),
        "סטופ": round(stop, 2),
        "יעד 1": round(target1, 2),
        "יעד 2": round(target2, 2),
        "סיכון בדולר": round(risk_dollars, 2),
        "כמות מניות משוערת": shares,
        "יחס סיכון/סיכוי": round(abs(target1-entry)/per_share_risk, 2) if per_share_risk else None,
    }

    risk_plan = {
        "גודל חשבון": account_size,
        "סיכון %": risk_pct,
        "סיכון מקסימלי": round(risk_dollars, 2),
        "סיכון ליחידה": round(per_share_risk, 2),
        "כמות יחידות": shares,
    }

    summary = (
        f"{symbol}: ציון {score}/100, אמינות {confidence}%, החלטה {action}. "
        f"המגמה {trend}. מחיר אחרון {entry:.2f}. תמיכה {support:.2f}, התנגדות {resistance:.2f}. "
        f"Max Pain: {options.get('max_pain')}. Call Wall: {options.get('call_wall')}. Put Wall: {options.get('put_wall')}."
    )

    return {
        "symbol": symbol, "score": score, "confidence": confidence, "trend": trend, "action": action,
        "risk": risk, "last_close": entry, "checks": checks, "summary": summary,
        "trade_plan": trade_plan, "risk_plan": risk_plan
    }
