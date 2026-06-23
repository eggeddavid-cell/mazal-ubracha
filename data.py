import yfinance as yf
import pandas as pd
import streamlit as st

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_history(symbol: str, period="1mo", interval="15m"):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=period, interval=interval, auto_adjust=False, timeout=20)
        if df is None or df.empty:
            return pd.DataFrame(), "לא התקבלו נתוני מחיר מ־Yahoo. נסה סימול אחר או תקופה קצרה יותר."
        df = df.rename(columns=str.title).dropna()
        needed = {"Open", "High", "Low", "Close", "Volume"}
        if not needed.issubset(set(df.columns)):
            return pd.DataFrame(), "חסרים נתוני OHLCV."
        return df, None
    except Exception as e:
        msg = str(e)
        if "RateLimit" in msg or "Too Many Requests" in msg or "429" in msg:
            return pd.DataFrame(), "Yahoo Finance חסם זמנית את הבקשות. המתן 5–10 דקות ונסה שוב."
        return pd.DataFrame(), f"שגיאה במשיכת נתונים: {msg}"

@st.cache_data(ttl=900, show_spinner=False)
def get_news(symbol: str):
    try:
        items = yf.Ticker(symbol).news or []
        return [{"title": x.get("title",""), "publisher": x.get("publisher",""), "link": x.get("link","")} for x in items[:10]]
    except Exception:
        return []
