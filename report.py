from indicators import score_trend

def build_trade_plan(df, levels, trend):
    last = float(df["Close"].iloc[-1])
    support = float(levels["support"])
    resistance = float(levels["resistance"])
    price_range = max(resistance - support, last * 0.005)

    if trend == "שורית":
        entry = round(max(last, resistance), 2)
        stop = round(support, 2)
        target1 = round(entry + price_range * 0.6, 2)
        target2 = round(entry + price_range * 1.0, 2)
    elif trend == "דובית":
        entry = round(min(last, support), 2)
        stop = round(resistance, 2)
        target1 = round(entry - price_range * 0.6, 2)
        target2 = round(entry - price_range * 1.0, 2)
    else:
        entry = round(last, 2)
        stop = round(support, 2)
        target1 = round(resistance, 2)
        target2 = round(resistance + price_range * 0.5, 2)

    risk = abs(entry - stop)
    reward = abs(target1 - entry)
    rr = round(reward / risk, 2) if risk else None

    return {
        "כיוון": trend,
        "כניסה אפשרית": entry,
        "סטופ": stop,
        "יעד 1": target1,
        "יעד 2": target2,
        "יחס סיכון/סיכוי": rr,
    }

def build_report(symbol, df, levels, options, news_items):
    score, trend, risk, checks = score_trend(df, options)
    last = df.iloc[-1]
    trade_plan = build_trade_plan(df, levels, trend)

    parts = [
        f"{symbol}: מגמה {trend} בציון {score}/100.",
        f"מחיר אחרון {last['Close']:.2f}.",
        f"תמיכה {levels['support']} | התנגדות {levels['resistance']}."
    ]
    parts.append("המחיר מעל VWAP — יתרון לקונים." if last["Close"] > last["VWAP"] else "המחיר מתחת VWAP — יתרון למוכרים.")
    if last["RSI"] > 75:
        parts.append("RSI גבוה — סיכון למימוש קצר.")
    elif last["RSI"] < 30:
        parts.append("RSI במכירת יתר — ייתכן תיקון.")
    else:
        parts.append("RSI ללא קיצון חריג.")
    if options and options.get("put_call_volume_ratio") is not None:
        pcr = options["put_call_volume_ratio"]
        if pcr < 0.8:
            parts.append("האופציות נוטות שורי לפי Put/Call נמוך.")
        elif pcr > 1.2:
            parts.append("האופציות נוטות הגנתי/דובי לפי Put/Call גבוה.")
        else:
            parts.append("האופציות מאוזנות יחסית.")

    return {
        "symbol": symbol,
        "score": score,
        "trend": trend,
        "risk": risk,
        "last_close": float(last["Close"]),
        "checks": checks,
        "summary": " ".join(parts),
        "trade_plan": trade_plan,
    }
