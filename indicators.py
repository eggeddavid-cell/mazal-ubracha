import numpy as np
import pandas as pd

def add_indicators(df):
    df = df.copy()
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (typical * df["Volume"]).cumsum() / df["Volume"].replace(0, np.nan).cumsum()
    for span in [20, 50, 200]:
        df[f"EMA{span}"] = df["Close"].ewm(span=span, adjust=False).mean()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["STD20"] = df["Close"].rolling(20).std()
    df["BB_Upper"] = df["SMA20"] + 2 * df["STD20"]
    df["BB_Lower"] = df["SMA20"] - 2 * df["STD20"]
    df["BB_Middle"] = df["SMA20"]
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    tr = pd.concat([(df["High"]-df["Low"]), (df["High"]-df["Close"].shift()).abs(), (df["Low"]-df["Close"].shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    df["Volume_MA20"] = df["Volume"].rolling(20).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_MA20"]
    return df.dropna()

def detect_levels(df):
    recent = df.tail(120)
    support = round(float(recent["Low"].quantile(0.10)), 2)
    resistance = round(float(recent["High"].quantile(0.90)), 2)
    return {"מחיר אחרון": round(float(df["Close"].iloc[-1]), 2), "תמיכה": support, "התנגדות": resistance, "תמיכת קיצון": round(float(recent["Low"].min()), 2), "התנגדות קיצון": round(float(recent["High"].max()), 2), "פריצה מעל": resistance, "חולשה מתחת": support, "support": support, "resistance": resistance}

def detect_patterns(df):
    out = []
    for idx, row in df.tail(10).iterrows():
        body = abs(row["Close"] - row["Open"])
        rng = max(row["High"] - row["Low"], 0.0001)
        upper = row["High"] - max(row["Open"], row["Close"])
        lower = min(row["Open"], row["Close"]) - row["Low"]
        if lower >= body * 2 and upper <= body * 1.2 and body / rng <= 0.45:
            out.append({"זמן": str(idx), "תבנית": "פטיש", "כיוון": "שורי", "עוצמה": "בינונית/גבוהה"})
        if upper >= body * 2 and lower <= body * 1.2 and body / rng <= 0.45:
            out.append({"זמן": str(idx), "תבנית": "כוכב נופל", "כיוון": "דובי", "עוצמה": "בינונית"})
        if body / rng <= 0.1:
            out.append({"זמן": str(idx), "תבנית": "דוג׳י", "כיוון": "ניטרלי", "עוצמה": "בינונית"})
    if len(df) >= 2:
        p, c = df.iloc[-2], df.iloc[-1]
        if c["Close"] > c["Open"] and p["Close"] < p["Open"] and c["Close"] > p["Open"] and c["Open"] < p["Close"]:
            out.append({"זמן": str(df.index[-1]), "תבנית": "Bullish Engulfing", "כיוון": "שורי", "עוצמה": "גבוהה"})
        if c["Close"] < c["Open"] and p["Close"] > p["Open"] and c["Open"] > p["Close"] and c["Close"] < p["Open"]:
            out.append({"זמן": str(df.index[-1]), "תבנית": "Bearish Engulfing", "כיוון": "דובי", "עוצמה": "גבוהה"})
    return out if out else [{"זמן": "-", "תבנית": "לא זוהתה", "כיוון": "ניטרלי", "עוצמה": "-"}]

def compute_market_regime(df):
    last = df.iloc[-1]
    bullish_stack = last["Close"] > last["EMA20"] > last["EMA50"]
    bearish_stack = last["Close"] < last["EMA20"] < last["EMA50"]
    atr_pct = float(last["ATR"] / last["Close"] * 100)
    regime = "מגמה עולה" if bullish_stack else "מגמה יורדת" if bearish_stack else "דשדוש/מעורב"
    return {"regime": regime, "atr_pct": round(atr_pct, 2), "above_vwap": bool(last["Close"] > last["VWAP"]), "volume_ratio": round(float(last["Volume_Ratio"]), 2)}
