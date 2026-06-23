import yfinance as yf
import pandas as pd
import streamlit as st

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_history(symbol, period="1mo", interval="15m"):
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False, timeout=25)
        if df is None or df.empty:
            return pd.DataFrame(), "לא התקבלו נתוני מחיר."
        return df.rename(columns=str.title).dropna(), None
    except Exception as e:
        msg = str(e)
        if "RateLimit" in msg or "429" in msg or "Too Many Requests" in msg:
            return pd.DataFrame(), "Yahoo חסם זמנית בקשות. המתן 5–10 דקות או נסה 5d/15m."
        return pd.DataFrame(), f"שגיאת נתונים: {msg}"

@st.cache_data(ttl=900, show_spinner=False)
def get_option_chain_full(symbol):
    try:
        t = yf.Ticker(symbol)
        exps = t.options
        if not exps:
            return {"available": False}
        exp = exps[0]
        ch = t.option_chain(exp)
        return {"available": True, "expiration": exp, "calls": ch.calls.copy(), "puts": ch.puts.copy()}
    except Exception:
        return {"available": False}
