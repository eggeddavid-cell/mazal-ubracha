import pandas as pd
import numpy as np

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
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

    return df

def detect_levels(df: pd.DataFrame):
    recent = df.tail(60)
    last_close = float(df["Close"].iloc[-1])
    support = float(recent["Low"].rolling(5).min().dropna().iloc[-10:].min())
    resistance = float(recent["High"].rolling(5).max().dropna().iloc[-10:].max())

    return {
        "last_close": round(last_close, 2),
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "bullish_above": round(resistance, 2),
        "bearish_below": round(support, 2),
    }

def score_trend(df: pd.DataFrame, options=None):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    score = 50
    checks = []

    def add(name, condition, weight):
        nonlocal score
        score += weight if condition else -weight
        checks.append({"בדיקה": name, "תוצאה": "חיובי" if condition else "שלילי", "משקל": weight})

    add("מחיר מעל VWAP", last["Close"] > last["VWAP"], 12)
    add("MACD מעל Signal", last["MACD"] > last["MACD_Signal"], 10)
    add("RSI מעל 50", last["RSI"] > 50, 8)
    add("RSI לא בקניית יתר קיצונית", last["RSI"] < 75, 5)
    add("Volume מעל ממוצע", last["Volume_Ratio"] > 1, 8)
    add("סגירה עולה מול נר קודם", last["Close"] > prev["Close"], 7)

    if options:
        pcr = options.get("put_call_volume_ratio")
        if pcr is not None:
            bullish = pcr < 0.9
            score += 8 if bullish else -8
            checks.append({"בדיקה": "Put/Call Volume Ratio", "תוצאה": "חיובי" if bullish else "שלילי", "משקל": 8})

    score = max(0, min(100, int(score)))

    if score >= 70:
        trend = "שורית"
    elif score <= 35:
        trend = "דובית"
    else:
        trend = "ניטרלית"

    risk = "גבוה" if last["RSI"] > 75 or last["Volume_Ratio"] > 3 else "בינוני"

    return score, trend, risk, checks
