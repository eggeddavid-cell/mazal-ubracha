from indicators import score_trend

def build_trade_plan(df, levels, trend):
    last, support, resistance = float(df["Close"].iloc[-1]), float(levels["support"]), float(levels["resistance"])
    price_range = max(resistance - support, last * 0.005)
    if trend == "שורית":
        entry, stop = round(max(last, resistance), 2), round(support, 2)
        target1, target2 = round(entry + price_range * 0.6, 2), round(entry + price_range, 2)
    elif trend == "דובית":
        entry, stop = round(min(last, support), 2), round(resistance, 2)
        target1, target2 = round(entry - price_range * 0.6, 2), round(entry - price_range, 2)
    else:
        entry, stop, target1, target2 = round(last, 2), round(support, 2), round(resistance, 2), round(resistance + price_range * 0.5, 2)
    risk, reward = abs(entry - stop), abs(target1 - entry)
    return {"כיוון": trend, "כניסה אפשרית": entry, "סטופ": stop, "יעד 1": target1, "יעד 2": target2, "יחס סיכון/סיכוי": round(reward / risk, 2) if risk else None}

def decide_action(score, trend):
    if trend == "שורית" and score >= 75:
        return "CALL"
    if trend == "דובית" and score <= 30:
        return "PUT"
    return "WAIT"

def build_report(symbol, df, levels, options, news_items, patterns):
    score, trend, risk, checks = score_trend(df, options, patterns)
    last = df.iloc[-1]
    trade_plan = build_trade_plan(df, levels, trend)
    action = decide_action(score, trend)
    parts = [f"{symbol}: מגמה {trend} בציון {score}/100.", f"החלטה: {action}.", f"מחיר אחרון {last['Close']:.2f}.", f"תמיכה {levels['support']} | התנגדות {levels['resistance']}."]
    parts.append("המחיר מעל VWAP — יתרון לקונים." if last["Close"] > last["VWAP"] else "המחיר מתחת VWAP — יתרון למוכרים.")
    if last["RSI"] > 75:
        parts.append("RSI גבוה — סיכון למימוש קצר.")
    elif last["RSI"] < 30:
        parts.append("RSI במכירת יתר — ייתכן תיקון.")
    else:
        parts.append("RSI ללא קיצון חריג.")
    if options and options.get("put_call_volume_ratio") is not None:
        pcr = options["put_call_volume_ratio"]
        parts.append("האופציות נוטות שורי לפי Put/Call נמוך." if pcr < 0.8 else "האופציות נוטות הגנתי/דובי לפי Put/Call גבוה." if pcr > 1.2 else "האופציות מאוזנות יחסית.")
    return {"symbol": symbol, "score": score, "trend": trend, "action": action, "risk": risk, "last_close": float(last["Close"]), "checks": checks, "summary": " ".join(parts), "trade_plan": trade_plan}
