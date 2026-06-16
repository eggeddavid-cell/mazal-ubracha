from indicators import score_trend

def build_report(symbol, df, levels, options, news_items):
    score, trend, risk, checks = score_trend(df, options)
    last = df.iloc[-1]

    summary = []
    summary.append(f"הסימול {symbol} מציג כרגע מגמה {trend} בציון {score}/100.")
    summary.append(f"המחיר האחרון הוא {last['Close']:.2f}.")
    summary.append(f"תמיכה קרובה: {levels['support']}, התנגדות קרובה: {levels['resistance']}.")

    if last["Close"] > last["VWAP"]:
        summary.append("המחיר מעל VWAP ולכן השליטה היומית נוטה לקונים.")
    else:
        summary.append("המחיר מתחת VWAP ולכן השליטה היומית נוטה למוכרים.")

    if last["RSI"] > 75:
        summary.append("שים לב: RSI גבוה מאוד ועלול להופיע מימוש קצר.")
    elif last["RSI"] < 30:
        summary.append("RSI במכירת יתר, ייתכן ניסיון תיקון.")
    else:
        summary.append("RSI אינו בקיצון חריג.")

    if options:
        pcr = options.get("put_call_volume_ratio")
        if pcr is not None:
            if pcr < 0.8:
                summary.append("שוק האופציות מראה נטייה שורית לפי Put/Call נמוך.")
            elif pcr > 1.2:
                summary.append("שוק האופציות מראה נטייה דובית/הגנתית לפי Put/Call גבוה.")
            else:
                summary.append("שוק האופציות מאוזן יחסית לפי Put/Call.")

    if news_items:
        summary.append("קיימות חדשות עדכניות ולכן יש לבדוק האם הן תומכות בכיוון הטכני.")

    return {
        "symbol": symbol,
        "score": score,
        "trend": trend,
        "risk": risk,
        "last_close": float(last["Close"]),
        "checks": checks,
        "summary": " ".join(summary),
    }
