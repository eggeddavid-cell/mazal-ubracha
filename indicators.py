import numpy as np
import pandas as pd

def _daily_vwap(df):
    out = []
    for _, g in df.groupby(df.index.date):
        typical = (g["High"] + g["Low"] + g["Close"]) / 3
        vwap = (typical * g["Volume"]).cumsum() / g["Volume"].replace(0, np.nan).cumsum()
        out.append(vwap)
    return pd.concat(out).sort_index()

def add_indicators(df):
    df = df.copy()
    df["VWAP"] = _daily_vwap(df)
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["SMA20"] = df["Close"].rolling(20).mean()
    std = df["Close"].rolling(20).std()
    df["BB_Upper"] = df["SMA20"] + 2 * std
    df["BB_Lower"] = df["SMA20"] - 2 * std
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["SMA20"]
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - df["Close"].shift()).abs()
    tr3 = (df["Low"] - df["Close"].shift()).abs()
    df["TR"] = np.maximum.reduce([tr1, tr2, tr3])
    df["ATR"] = df["TR"].rolling(14).mean()
    df["ATR_Pct"] = df["ATR"] / df["Close"]
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    low14 = df["Low"].rolling(14).min()
    high14 = df["High"].rolling(14).max()
    df["Stoch_K"] = 100 * (df["Close"] - low14) / (high14 - low14).replace(0, np.nan)
    df["Stoch_D"] = df["Stoch_K"].rolling(3).mean()
    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr = df["TR"].rolling(14).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(14).sum() / atr.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(14).sum() / atr.replace(0, np.nan)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    df["ADX"] = dx.rolling(14).mean()
    df["Plus_DI"] = plus_di
    df["Minus_DI"] = minus_di
    df["Volume_MA20"] = df["Volume"].rolling(20).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_MA20"].replace(0, np.nan)
    df["OBV"] = (np.sign(df["Close"].diff()).fillna(0) * df["Volume"]).cumsum()
    df["OBV_EMA"] = df["OBV"].ewm(span=20, adjust=False).mean()
    df["Return_5"] = df["Close"].pct_change(5)
    return df.dropna()

def detect_levels(df):
    recent = df.tail(120)
    support = float(recent["Low"].rolling(5).min().dropna().quantile(0.15))
    resistance = float(recent["High"].rolling(5).max().dropna().quantile(0.85))
    recent_low = float(recent["Low"].min())
    recent_high = float(recent["High"].max())
    if support > df["Close"].iloc[-1]: support = recent_low
    if resistance < df["Close"].iloc[-1]: resistance = recent_high
    return {"מחיר אחרון": round(float(df["Close"].iloc[-1]),2), "תמיכה קרובה": round(support,2), "התנגדות קרובה": round(resistance,2), "שפל מדגם": round(recent_low,2), "שיא מדגם": round(recent_high,2), "support": round(support,2), "resistance": round(resistance,2)}

def detect_patterns(df):
    out=[]
    for idx,row in df.tail(8).iterrows():
        body=abs(row["Close"]-row["Open"]); rng=max(row["High"]-row["Low"],0.0001)
        upper=row["High"]-max(row["Open"],row["Close"]); lower=min(row["Open"],row["Close"])-row["Low"]
        bull=row["Close"]>row["Open"]; bear=row["Close"]<row["Open"]
        if lower>=body*2 and upper<=body*1.2 and body/rng<=0.45: out.append({"זמן":str(idx),"תבנית":"פטיש","כיוון":"שורית","עוצמה":"בינונית/גבוהה"})
        if upper>=body*2 and lower<=body*1.2 and body/rng<=0.45: out.append({"זמן":str(idx),"תבנית":"כוכב נופל","כיוון":"דובית","עוצמה":"בינונית"})
        if body/rng<=0.12: out.append({"זמן":str(idx),"תבנית":"דוג'י","כיוון":"ניטרלית","עוצמה":"נמוכה/בינונית"})
        if bull and body/rng>0.65: out.append({"זמן":str(idx),"תבנית":"נר ירוק חזק","כיוון":"שורית","עוצמה":"בינונית"})
        if bear and body/rng>0.65: out.append({"זמן":str(idx),"תבנית":"נר אדום חזק","כיוון":"דובית","עוצמה":"בינונית"})
    if len(df)>=2:
        p,c=df.iloc[-2],df.iloc[-1]
        if c["Close"]>c["Open"] and p["Close"]<p["Open"] and c["Close"]>p["Open"] and c["Open"]<p["Close"]: out.append({"זמן":str(df.index[-1]),"תבנית":"Bullish Engulfing","כיוון":"שורית","עוצמה":"גבוהה"})
        if c["Close"]<c["Open"] and p["Close"]>p["Open"] and c["Open"]>p["Close"] and c["Close"]<p["Open"]: out.append({"זמן":str(df.index[-1]),"תבנית":"Bearish Engulfing","כיוון":"דובית","עוצמה":"גבוהה"})
    return out if out else [{"זמן":"-","תבנית":"לא זוהתה","כיוון":"ניטרלית","עוצמה":"-"}]
