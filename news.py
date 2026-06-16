import yfinance as yf

def get_news(symbol: str):
    try:
        items = yf.Ticker(symbol).news or []
        return [{"title": x.get("title",""), "publisher": x.get("publisher",""), "link": x.get("link","")} for x in items[:10]]
    except Exception:
        return []
