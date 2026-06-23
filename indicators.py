import pandas as pd
import numpy as np

def add_indicators(df):
    df = df.copy()
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (typical * df["Volume"]).cumsum() / df["Volume"].replace(0, np.nan).cumsum()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["BB_Middle"] = df["SMA20"]
    df["BB_Upper"] = df["SMA20"] + 2 * df["STD20"]
    df["BB_Lower"] = df["SMA20"] - 2 * df["STD20"]
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["Volume_MA20"] = df["Volume"].rolling(20).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_MA20"]
    return df.dropna()

def detect_levels(df):
    recent = df.tail(80)
    support = round(float(recent["Low"].min()), 2)
    resistance = round(float(recent["High"].max()), 2)
    return {"מחיר אחרון": round(float(df["Close"].iloc[-1]), 2), "תמיכה": support, "התנגדות": resistance, "פריצה מעל": resistance, "חולשה מתחת": support, "support": support, "resistance": resistance}

def detect_patterns(df):
    out = []
    for idx, row in df.tail(8).iterrows():
        body = abs(row["Close"] - row["Open"])
        rng = max(row["High"] - row["Low"], 0.0001)
        upper = row["High"] - max(row["Open"], row["Close"])
        lower = min(row["Open"], row["Close"]) - row["Low"]
        if lower >= body * 2 and upper <= body * 1.2 and body / rng <= 0.45:
            out.append({"זמן": str(idx), "תבנית": "פטיש", "משמעות": "אפשרות להיפוך שורי", "עוצמה": "בינונית/גבוהה"})
        if upper >= body * 2 and lower <= body * 1.2 and body / rng <= 0.45:
            out.append({"זמן": str(idx), "תבנית": "כוכב נופל", "משמעות": "אפשרות לחולשה/היפוך דובי", "עוצמה": "בינונית"})
        if body / rng <= 0.12:
            out.append({"זמן": str(idx), "תבנית": "דוג'י", "משמעות": "חוסר החלטיות", "עוצמה": "נמוכה/בינונית"})
    if len(df) >= 2:
        p, c = df.iloc[-2], df.iloc[-1]
        if c["Close"] > c["Open"] and p["Close"] < p["Open"] and c["Close"] > p["Open"] and c["Open"] < p["Close"]:
            out.append({"זמן": str(df.index[-1]), "תבנית": "Bullish Engulfing", "משמעות": "איתות שורי", "עוצמה": "גבוהה"})
        if c["Close"] < c["Open"] and p["Close"] > p["Open"] and c["Open"] > p["Close"] and c["Close"] < p["Open"]:
            out.append({"זמן": str(df.index[-1]), "תבנית": "Bearish Engulfing", "משמעות": "איתות דובי", "עוצמה": "גבוהה"})
    return out if out else [{"זמן": "-", "תבנית": "לא זוהתה", "משמעות": "אין תבנית נרות בולטת בנרות האחרונים", "עוצמה": "-"}]

def score_trend(df, options=None, patterns=None):
    last, prev = df.iloc[-1], df.iloc[-2]
    score, checks = 50, []
    def add(name, condition, weight):
        nonlocal score
        score += weight if condition else -weight
        checks.append({"בדיקה": name, "תוצאה": "חיובי" if condition else "שלילי", "משקל": weight})
    add("מחיר מעל VWAP", last["Close"] > last["VWAP"], 12)
    add("MACD מעל Signal", last["MACD"] > last["MACD_Signal"], 10)
    add("RSI מעל 50", last["RSI"] > 50, 8)
    add("RSI לא בקיצון עליון", last["RSI"] < 75, 5)
    add("Volume מעל ממוצע", last["Volume_Ratio"] > 1, 8)
    add("סגירה עולה מול נר קודם", last["Close"] > prev["Close"], 7)
    if options and options.get("put_call_volume_ratio") is not None:
        bullish = options["put_call_volume_ratio"] < 0.9
        score += 8 if bullish else -8
        checks.append({"בדיקה": "Put/Call Volume Ratio", "תוצאה": "חיובי" if bullish else "שלילי", "משקל": 8})
    if patterns:
        names = " ".join([p.get("תבנית","") for p in patterns])
        if "פטיש" in names or "Bullish Engulfing" in names:
            score += 6
            checks.append({"בדיקה": "תבנית נרות שורית", "תוצאה": "חיובי", "משקל": 6})
        if "כוכב נופל" in names or "Bearish Engulfing" in names:
            score -= 6
            checks.append({"בדיקה": "תבנית נרות דובית", "תוצאה": "שלילי", "משקל": 6})
    score = max(0, min(100, int(score)))
    trend = "שורית" if score >= 70 else "דובית" if score <= 35 else "ניטרלית"
    risk = "גבוה" if last["RSI"] > 75 or last["Volume_Ratio"] > 3 else "בינוני"
    return score, trend, risk, checks
