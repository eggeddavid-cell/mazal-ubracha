import streamlit as st
import pandas as pd
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
import requests

def _get_secret(name):
    try:
        return st.secrets.get(name, None)
    except Exception:
        return None

@st.cache_data(ttl=600, show_spinner=False)
def get_market_data(symbol: str, interval="15min"):
    symbol = (symbol or "").upper().strip()

    av_key = _get_secret("ALPHA_VANTAGE_API_KEY")
    if av_key:
        df, err = _alpha_vantage_data(symbol, interval, av_key)
        if df is not None and not df.empty:
            return df, "Alpha Vantage", None

    fmp_key = _get_secret("FMP_API_KEY")
    if fmp_key:
        df, err = _fmp_historical_data(symbol, interval, fmp_key)
        if df is not None and not df.empty:
            return df, "FMP Historical", None

    df, err = _yahoo_data(symbol, interval)
    if df is not None and not df.empty:
        return df, "Yahoo fallback", None

    return pd.DataFrame(), "none", err or "לא התקבלו נתונים משום מקור. בדוק Secrets או נסה טיים־פריים אחר."

def _alpha_vantage_data(symbol, interval, key):
    try:
        ts = TimeSeries(key=key, output_format="pandas")
        if interval == "daily":
            data, _ = ts.get_daily(symbol=symbol, outputsize="compact")
        else:
            data, _ = ts.get_intraday(symbol=symbol, interval=interval, outputsize="full")
        if data is None or data.empty:
            return pd.DataFrame(), "Alpha Vantage לא החזיר נתונים."
        data = data.rename(columns={
            "1. open":"Open","2. high":"High","3. low":"Low","4. close":"Close","5. volume":"Volume"
        })
        data = data[["Open","High","Low","Close","Volume"]].sort_index()
        data.index = pd.to_datetime(data.index)
        return data.dropna(), None
    except Exception as e:
        return pd.DataFrame(), str(e)

def _fmp_interval(interval):
    return {
        "5min": "5min",
        "15min": "15min",
        "30min": "30min",
        "60min": "1hour",
        "daily": "daily",
    }.get(interval, "15min")

def _fmp_historical_data(symbol, interval, key):
    try:
        if interval == "daily":
            urls = [
                f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=260&apikey={key}",
                f"https://financialmodelingprep.com/stable/historical-price-eod/full?symbol={symbol}&apikey={key}",
            ]
        else:
            fmp_iv = _fmp_interval(interval)
            urls = [
                f"https://financialmodelingprep.com/api/v3/historical-chart/{fmp_iv}/{symbol}?apikey={key}",
                f"https://financialmodelingprep.com/stable/historical-chart/{fmp_iv}?symbol={symbol}&apikey={key}",
            ]

        for url in urls:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()

            if isinstance(data, dict) and "historical" in data:
                data = data["historical"]
            elif isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                data = data["data"]

            if not isinstance(data, list) or not data:
                continue

            df = pd.DataFrame(data)
            colmap = {
                "open": "Open", "high": "High", "low": "Low", "close": "Close",
                "volume": "Volume", "date": "Date"
            }
            df = df.rename(columns=colmap)

            needed = ["Open", "High", "Low", "Close", "Volume"]
            if not set(needed).issubset(df.columns):
                continue

            date_col = "Date" if "Date" in df.columns else "date" if "date" in df.columns else None
            if date_col:
                df.index = pd.to_datetime(df[date_col])
            else:
                continue

            df = df[needed].apply(pd.to_numeric, errors="coerce").dropna().sort_index()
            if len(df) >= 80:
                return df, None

        return pd.DataFrame(), "FMP לא החזיר מספיק נרות היסטוריים."
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
        if df is None or df.empty:
            return pd.DataFrame(), "Yahoo לא החזיר נתונים."
        df = df.rename(columns=str.title)
        return df[["Open","High","Low","Close","Volume"]].dropna(), None
    except Exception as e:
        msg = str(e)
        if "Too Many Requests" in msg or "Rate" in msg or "429" in msg:
            return pd.DataFrame(), "Yahoo Finance חסם זמנית את הבקשות."
        return pd.DataFrame(), msg

@st.cache_data(ttl=900, show_spinner=False)
def get_news(symbol: str, limit: int = 10):
    symbol = (symbol or "").upper().strip()

    fmp_key = _get_secret("FMP_API_KEY")
    if fmp_key:
        items = _fmp_news(symbol, fmp_key, limit)
        if items:
            return items[:limit]

    av_key = _get_secret("ALPHA_VANTAGE_API_KEY")
    if av_key:
        items = _alpha_news(symbol, av_key, limit)
        if items:
            return items[:limit]

    return _yahoo_news(symbol, limit)[:limit]

def _fmp_news(symbol, key, limit):
    urls = [
        f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit={limit}&apikey={key}",
        f"https://financialmodelingprep.com/stable/news/stock?symbols={symbol}&limit={limit}&apikey={key}",
        f"https://financialmodelingprep.com/stable/stock-news?symbols={symbol}&limit={limit}&apikey={key}",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=12)
            if r.status_code != 200:
                continue
            data = r.json()
            if isinstance(data, dict):
                for k in ["data", "news", "results", "articles"]:
                    if isinstance(data.get(k), list):
                        data = data[k]
                        break
            if not isinstance(data, list) or not data:
                continue
            out = []
            for x in data:
                if not isinstance(x, dict):
                    continue
                title = x.get("title") or x.get("headline") or ""
                if not title:
                    continue
                out.append({
                    "title": title,
                    "publisher": x.get("site") or x.get("publisher") or x.get("source") or "FMP",
                    "date": x.get("publishedDate") or x.get("date") or "",
                    "summary": x.get("text") or x.get("summary") or "",
                    "link": x.get("url") or x.get("link") or "",
                    "source": "FMP"
                })
            if out:
                return out
        except Exception:
            continue
    return []

def _alpha_news(symbol, key, limit):
    try:
        url = "https://www.alphavantage.co/query"
        params = {"function": "NEWS_SENTIMENT", "tickers": symbol, "limit": limit, "apikey": key}
        r = requests.get(url, params=params, timeout=12)
        if r.status_code != 200:
            return []
        data = r.json()
        feed = data.get("feed", [])
        return [{
            "title": x.get("title", ""),
            "publisher": x.get("source", "Alpha Vantage"),
            "date": x.get("time_published", ""),
            "summary": x.get("summary", ""),
            "link": x.get("url", ""),
            "source": "Alpha Vantage"
        } for x in feed]
    except Exception:
        return []

def _yahoo_news(symbol, limit):
    try:
        items = yf.Ticker(symbol).news or []
        return [{
            "title": x.get("title", ""),
            "publisher": x.get("publisher", "Yahoo"),
            "date": "",
            "summary": x.get("summary", ""),
            "link": x.get("link", ""),
            "source": "Yahoo"
        } for x in items[:limit]]
    except Exception:
        return []
