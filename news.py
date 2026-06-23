import yfinance as yf
import streamlit as st

@st.cache_data(ttl=900, show_spinner=False)
def get_news(symbol: str):
    try:
        items = yf.Ticker(symbol).news or []
        return [{"title": x.get("title",""), "publisher": x.get("publisher",""), "link": x.get("link","")} for x in items[:10]]
    except Exception:
        return []
