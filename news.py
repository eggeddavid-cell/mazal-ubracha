import yfinance as yf

def get_news(symbol: str):
    try:
        news = yf.Ticker(symbol).news or []
        out = []
        for item in news[:10]:
            out.append({
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
            })
        return out
    except Exception:
        return []
