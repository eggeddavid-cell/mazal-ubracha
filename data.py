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
            return pd.DataFrame(), "Yahoo Finance חסם זמנית את הבקשות בגלל Rate Limit. המתן 5–10 דקות ונסה שוב עם 5d / 15m."
        return pd.DataFrame(), f"שגיאה במשיכת נתונים: {msg}"

@st.cache_data(ttl=600, show_spinner=False)
def get_option_chain(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return {}
        exp = expirations[0]
        chain = ticker.option_chain(exp)
        calls, puts = chain.calls, chain.puts
        call_vol = int(calls["volume"].fillna(0).sum())
        put_vol = int(puts["volume"].fillna(0).sum())
        call_oi = int(calls["openInterest"].fillna(0).sum())
        put_oi = int(puts["openInterest"].fillna(0).sum())
        return {
            "nearest_expiration": exp,
            "call_volume": call_vol,
            "put_volume": put_vol,
            "put_call_volume_ratio": round(put_vol / call_vol, 2) if call_vol else None,
            "call_open_interest": call_oi,
            "put_open_interest": put_oi,
            "put_call_oi_ratio": round(put_oi / call_oi, 2) if call_oi else None,
        }
    except Exception:
        return {}
