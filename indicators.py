import numpy as np
import pandas as pd

def _vwap(df):
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    return (typical * df["Volume"]).cumsum() / df["Volume"].replace(0, np.nan).cumsum()

def add_indicators(df):
    df = df.copy()
    df["VWAP"] = _vwap(df)
    for span in [9,20,50,200]:
        df[f"EMA{span}"] = df["Close"].ewm(span=span, adjust=False).mean()
    sma20 = df["Close"].rolling(20).mean(); std = df["Close"].rolling(20).std()
    df["BB_Upper"] = sma20 + 2*std; df["BB_Lower"] = sma20 - 2*std
    tr1 = df["High"] - df["Low"]; tr2 = (df["High"] - df["Close"].shift()).abs(); tr3 = (df["Low"] - df["Close"].shift()).abs()
    df["TR"] = np.maximum.reduce([tr1, tr2, tr3]); df["ATR"] = df["TR"].rolling(14).mean()
    delta = df["Close"].diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan); df["RSI"] = 100 - (100/(1+rs))
    ema12 = df["Close"].ewm(span=12, adjust=False).mean(); ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26; df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean(); df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    low14 = df["Low"].rolling(14).min(); high14 = df["High"].rolling(14).max()
    df["Stoch_K"] = 100*(df["Close"]-low14)/(high14-low14).replace(0, np.nan); df["Stoch_D"] = df["Stoch_K"].rolling(3).mean()
    up = df["High"].diff(); down = -df["Low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0); minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    atr = df["TR"].rolling(14).mean()
    df["Plus_DI"] = 100*pd.Series(plus_dm, index=df.index).rolling(14).sum()/atr.replace(0, np.nan)
    df["Minus_DI"] = 100*pd.Series(minus_dm, index=df.index).rolling(14).sum()/atr.replace(0, np.nan)
    dx = (abs(df["Plus_DI"]-df["Minus_DI"])/(df["Plus_DI"]+df["Minus_DI"]).replace(0, np.nan))*100
    df["ADX"] = dx.rolling(14).mean()
    df["Volume_MA20"] = df["Volume"].rolling(20).mean(); df["Volume_Ratio"] = df["Volume"]/df["Volume_MA20"].replace(0, np.nan)
    df["OBV"] = (np.sign(df["Close"].diff()).fillna(0)*df["Volume"]).cumsum(); df["OBV_EMA"] = df["OBV"].ewm(span=20, adjust=False).mean()
    df["Return_5"] = df["Close"].pct_change(5)
    return df.dropna()

def detect_levels(df):
    recent = df.tail(120)
    support = float(recent["Low"].rolling(5).min().dropna().quantile(0.15))
    resistance = float(recent["High"].rolling(5).max().dropna().quantile(0.85))
    support = min(support, float(df["Close"].iloc[-1])); resistance = max(resistance, float(df["Close"].iloc[-1]))
    return {"מחיר אחרון": round(float(df["Close"].iloc[-1]),2), "תמיכה קרובה": round(support,2), "התנגדות קרובה": round(resistance,2), "support": round(support,2), "resistance": round(resistance,2)}

def detect_patterns(df):
    out = []
    for idx, row in df.tail(8).iterrows():
        body = abs(row["Close"]-row["Open"]); rng = max(row["High"]-row["Low"], 0.0001)
        upper = row["High"]-max(row["Open"],row["Close"]); lower = min(row["Open"],row["Close"])-row["Low"]
        if lower >= body*2 and upper <= body*1.2 and body/rng <= 0.45: out.append({"זמן":str(idx),"תבנית":"פטיש","כיוון":"שורית","עוצמה":"בינונית/גבוהה"})
        if upper >= body*2 and lower <= body*1.2 and body/rng <= 0.45: out.append({"זמן":str(idx),"תבנית":"כוכב נופל","כיוון":"דובית","עוצמה":"בינונית"})
        if body/rng <= 0.12: out.append({"זמן":str(idx),"תבנית":"דוג'י","כיוון":"ניטרלית","עוצמה":"בינונית"})
    return out if out else [{"זמן":"-","תבנית":"לא זוהתה","כיוון":"ניטרלית","עוצמה":"-"}]
