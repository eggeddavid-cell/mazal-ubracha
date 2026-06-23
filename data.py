import yfinance as yf
import pandas as pd
import streamlit as st

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_history(symbol: str, period="5d", interval="15m"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=False, timeout=20)
        if df is None or df.empty:
            return pd.DataFrame(), "לא התקבלו נתוני מחיר. נסה תקופה קצרה יותר כמו 5d או סימול אחר."
        return df.rename(columns=str.title).dropna(), None
    except Exception as e:
        msg = str(e)
        if "RateLimit" in msg or "Too Many Requests" in msg or "429" in msg:
            return pd.DataFrame(), "Yahoo Finance חסם זמנית את הבקשות. המתן 5–10 דקות ונסה 5d / 15m."
        return pd.DataFrame(), f"שגיאה במשיכת נתונים: {msg}"
