def build_pro_trade_decision(symbol, df, levels, patterns, regime, opt, account, risk_pct):
    last = df.iloc[-1]; prev = df.iloc[-2]
    score = 50; checks = []; pos = []; risks = []
    def add(name, condition, weight, good, bad):
        nonlocal score
        score += weight if condition else -weight
        checks.append({"בדיקה": name, "תוצאה": "חיובי" if condition else "שלילי", "משקל": weight})
        (pos if condition else risks).append({"גורם": name, "פירוט": good if condition else bad})
    add("מחיר מעל VWAP", last["Close"] > last["VWAP"], 10, "קונים שולטים תוך יומית", "המוכרים שולטים מתחת VWAP")
    add("EMA20 מעל EMA50", last["EMA20"] > last["EMA50"], 9, "מבנה מגמה חיובי", "מבנה מגמה חלש")
    add("MACD חיובי", last["MACD"] > last["MACD_Signal"], 8, "מומנטום משתפר", "מומנטום נחלש")
    add("RSI מעל 50", last["RSI"] > 50, 7, "כוח יחסי חיובי", "כוח יחסי חלש")
    add("RSI לא קיצוני", 35 < last["RSI"] < 72, 5, "אין קניית יתר/מכירת יתר קיצונית", "סיכון לקיצון RSI")
    add("Volume מעל ממוצע", last["Volume_Ratio"] > 1, 8, "המהלך נתמך במחזור", "חוסר אישור במחזור")
    add("סגירה מעל נר קודם", last["Close"] > prev["Close"], 5, "המשך קנייה בנר האחרון", "חולשה בנר האחרון")
    add("קרוב לפריצה", last["Close"] >= levels["resistance"] * 0.995, 6, "מחיר קרוב להתנגדות/פריצה", "עדיין לא מאיים על התנגדות")
    names = " ".join([p.get("תבנית", "") + p.get("כיוון", "") for p in patterns])
    if "שורי" in names:
        score += 6; checks.append({"בדיקה":"תבנית נרות שורית","תוצאה":"חיובי","משקל":6}); pos.append({"גורם":"תבנית נרות","פירוט":"זוהתה תבנית שורית"})
    if "דובי" in names:
        score -= 6; checks.append({"בדיקה":"תבנית נרות דובית","תוצאה":"שלילי","משקל":6}); risks.append({"גורם":"תבנית נרות","פירוט":"זוהתה תבנית דובית"})
    if opt.get("available"):
        pcr = opt.get("put_call_volume_ratio")
        if pcr is not None:
            if pcr < 0.8:
                score += 8; pos.append({"גורם":"אופציות","פירוט":"Put/Call נמוך - נטייה ל-Calls"})
            elif pcr > 1.2:
                score -= 8; risks.append({"גורם":"אופציות","פירוט":"Put/Call גבוה - הגנתי/דובי"})
        mp = opt.get("max_pain")
        if mp:
            if last["Close"] > mp:
                score += 3; pos.append({"גורם":"Max Pain","פירוט":"מחיר מעל Max Pain"})
            else:
                score -= 3; risks.append({"גורם":"Max Pain","פירוט":"מחיר מתחת Max Pain"})
    score = max(0, min(100, int(score)))
    trend = "שורית" if score >= 65 else "דובית" if score <= 35 else "ניטרלית"
    action = "CALL" if score >= 75 else "PUT" if score <= 28 else "WAIT"
    confidence = min(95, max(35, int(abs(score-50)*1.35 + 45)))
    price = float(last["Close"]); atr = float(last["ATR"]); support = float(levels["support"]); resistance = float(levels["resistance"])
    if action == "CALL":
        entry = max(price, resistance); stop = min(support, entry - 1.2*atr); t1 = entry + 1.5*atr; t2 = entry + 2.5*atr
    elif action == "PUT":
        entry = min(price, support); stop = max(resistance, entry + 1.2*atr); t1 = entry - 1.5*atr; t2 = entry - 2.5*atr
    else:
        entry = price; stop = support; t1 = resistance; t2 = resistance + atr
    risk_per_share = abs(entry - stop); dollar_risk = account * (risk_pct / 100); shares = int(dollar_risk / risk_per_share) if risk_per_share > 0 else 0
    rr = round(abs(t1-entry) / risk_per_share, 2) if risk_per_share else None
    risk_level = "גבוה" if regime["atr_pct"] > 3 or last["RSI"] > 75 else "בינוני" if regime["atr_pct"] > 1.5 else "נמוך/בינוני"
    summary = f'{symbol}: {action}. מגמה {trend}, ציון {score}/100, אמינות {confidence}%. מחיר {price:.2f}, תמיכה {support}, התנגדות {resistance}. '
    summary += "אין מספיק יתרון סטטיסטי לכניסה איכותית כרגע; עדיף להמתין לפריצה/שבירה עם מחזור." if action == "WAIT" else "יש קונפלואנס מספיק בין מחיר, מומנטום וניהול סיכון, אך חובה לעבוד עם סטופ."
    return {"symbol": symbol, "score": score, "confidence": confidence, "trend": trend, "action": action, "last_price": price, "risk_level": risk_level, "summary": summary, "checks": checks, "positive_factors": pos or [{"גורם":"אין", "פירוט":"לא נמצאו גורמים חזקים"}], "risk_factors": risks or [{"גורם":"אין חריג", "פירוט":"לא נמצאו סיכונים חריגים"}], "trade_plan": {"כיוון": trend, "פעולה": action, "כניסה": round(entry,2), "סטופ": round(stop,2), "יעד 1": round(t1,2), "יעד 2": round(t2,2), "יחס סיכון/סיכוי": rr}, "risk_management": {"סיכון לעסקה $": round(dollar_risk,2), "סיכון למניה $": round(risk_per_share,2), "כמות מניות תאורטית": shares, "ATR %": regime["atr_pct"], "Volume Ratio": regime["volume_ratio"]}}
