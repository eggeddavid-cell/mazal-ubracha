import streamlit as st
import pandas as pd
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries

def _get_secret(name):
    try: return st.secrets.get(name, None)
    except Exception: return None

@st.cache_data(ttl=300, show_spinner=False)
def get_market_data(symbol: str, interval="15min"):
    av_key = _get_secret("ALPHA_VANTAGE_API_KEY")
    if av_key:
        df, _ = _alpha_vantage_data(symbol, interval, av_key)
        if df is not None and not df.empty: return df, "Alpha Vantage", None
    df, err = _yahoo_data(symbol, interval)
    if df is not None and not df.empty: return df, "Yahoo fallback", None
    return pd.DataFrame(), "none", err or "לא התקבלו נתונים."

def _alpha_vantage_data(symbol, interval, key):
    try:
        ts = TimeSeries(key=key, output_format="pandas")
        if interval == "daily":
            data, _ = ts.get_daily(symbol=symbol, outputsize="compact")
        else:
            data, _ = ts.get_intraday(symbol=symbol, interval=interval, outputsize="full")
        if data is None or data.empty: return pd.DataFrame(), "Alpha Vantage לא החזיר נתונים."
        data = data.rename(columns={"1. open":"Open","2. high":"High","3. low":"Low","4. close":"Close","5. volume":"Volume"})
        data = data[["Open","High","Low","Close","Volume"]].sort_index()
        data.index = pd.to_datetime(data.index)
        return data.dropna(), None
    except Exception as e:
        return pd.DataFrame(), str(e)

def _yahoo_interval(interval):
    return {"5min":"5m","15min":"15m","30min":"30m","60min":"1h","daily":"1d"}.get(interval,"15m")

def _yahoo_period(interval):
    return "6mo" if interval == "daily" else "1mo"

def _yahoo_data(symbol, interval):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=_yahoo_period(interval), interval=_yahoo_interval(interval), auto_adjust=False, timeout=20)
        if df is None or df.empty: return pd.DataFrame(), "Yahoo לא החזיר נתונים."
        df = df.rename(columns=str.title)
        return df[["Open","High","Low","Close","Volume"]].dropna(), None
    except Exception as e:
        return pd.DataFrame(), str(e)

@st.cache_data(ttl=900, show_spinner=False)
def get_news(symbol: str):
    try:
        items = yf.Ticker(symbol).news or []
        return [{"title": x.get("title",""), "publisher": x.get("publisher",""), "link": x.get("link","")} for x in items[:10]]
    except Exception:
        return []
