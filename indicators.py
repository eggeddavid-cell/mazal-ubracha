import numpy as np

def add_indicators(df):
    df = df.copy()
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (typical * df["Volume"]).cumsum() / df["Volume"].replace(0, np.nan).cumsum()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["BB_Upper"] = df["SMA20"] + 2 * df["STD20"]
    df["BB_Lower"] = df["SMA20"] - 2 * df["STD20"]
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - df["Close"].shift()).abs()
    tr3 = (df["Low"] - df["Close"].shift()).abs()
    df["ATR"] = np.maximum.reduce([tr1, tr2, tr3])
    df["ATR"] = df["ATR"].rolling(14).mean()
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
    return out if out else [{"זמן": "-", "תבנית": "לא זוהתה", "משמעות": "אין תבנית בולטת", "עוצמה": "-"}]
