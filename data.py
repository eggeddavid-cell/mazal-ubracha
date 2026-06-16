import yfinance as yf
import pandas as pd

def get_stock_history(symbol: str, period="1mo", interval="15m") -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns=str.title)
    return df.dropna()

def get_option_chain(symbol: str):
    """
    מקור חינמי דרך Yahoo Finance.
    לדיוק מקצועי יותר באופציות: Polygon.io / Tradier / ORATS / CBOE LiveVol.
    """
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return {}

        exp = expirations[0]
        chain = ticker.option_chain(exp)

        calls = chain.calls
        puts = chain.puts

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
