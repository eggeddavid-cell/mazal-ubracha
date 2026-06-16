from indicators import score_trend

def build_report(symbol, df, levels, options, news_items):
    score, trend, risk, checks = score_trend(df, options)
    last = df.iloc[-1]
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
    }
