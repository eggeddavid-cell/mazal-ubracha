import math
import requests
import pandas as pd
import yfinance as yf
import streamlit as st
from datetime import date, timedelta

def _get_secret(name):
    try:
        return st.secrets.get(name, None)
    except Exception:
        return None

def _next_monthly_expiration():
    today = date.today()
    d = today + timedelta(days=1)
    # יעד פשוט: תאריך עתידי קרוב עד 45 יום
    return d.isoformat()

@st.cache_data(ttl=900, show_spinner=False)
def get_options_analysis(symbol: str, spot_price: float):
    token = _get_secret("TRADIER_TOKEN")
    if token:
        data = _from_tradier(symbol, token)
        if data.get("chain_table"):
            data["source"] = "tradier"
            return data

    poly = _get_secret("POLYGON_API_KEY")
    if poly:
        data = _from_polygon(symbol, poly, spot_price)
        if data.get("chain_table"):
            data["source"] = "polygon"
            return data

    data = _from_yahoo(symbol)
    if data.get("chain_table"):
        data["source"] = "yahoo_limited"
        return data

    return {"source": "none", "chain_table": [], "max_pain": None, "call_wall": None, "put_wall": None, "gex_bias": None}

def _from_tradier(symbol, token):
    try:
        base = "https://api.tradier.com/v1/markets/options"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        exp_r = requests.get(f"{base}/expirations", params={"symbol": symbol, "includeAllRoots": "true", "strikes": "false"}, headers=headers, timeout=15)
        exp_json = exp_r.json()
        dates = exp_json.get("expirations", {}).get("date", [])
        if isinstance(dates, str):
            dates = [dates]
        if not dates:
            return {}
        exp = dates[0]
        chain_r = requests.get(f"{base}/chains", params={"symbol": symbol, "expiration": exp, "greeks": "true"}, headers=headers, timeout=20)
        opts = chain_r.json().get("options", {}).get("option", [])
        if isinstance(opts, dict):
            opts = [opts]
        rows = []
        for o in opts:
            greeks = o.get("greeks") or {}
            rows.append({
                "strike": float(o.get("strike", 0)),
                "type": o.get("option_type"),
                "volume": int(o.get("volume") or 0),
                "openInterest": int(o.get("open_interest") or 0),
                "iv": float(greeks.get("mid_iv") or 0),
                "gamma": float(greeks.get("gamma") or 0),
            })
        return _analyze_chain(rows)
    except Exception:
        return {}

def _from_polygon(symbol, api_key, spot_price):
    try:
        url = "https://api.polygon.io/v3/snapshot/options/" + symbol
        params = {"limit": 250, "apiKey": api_key}
        r = requests.get(url, params=params, timeout=20)
        js = r.json()
        rows = []
        for item in js.get("results", []):
            details = item.get("details", {})
            greeks = item.get("greeks", {}) or {}
            day = item.get("day", {}) or {}
            oi = item.get("open_interest") or 0
            rows.append({
                "strike": float(details.get("strike_price", 0)),
                "type": "call" if details.get("contract_type") == "call" else "put",
                "volume": int(day.get("volume") or 0),
                "openInterest": int(oi or 0),
                "iv": float(item.get("implied_volatility") or 0),
                "gamma": float(greeks.get("gamma") or 0),
            })
        return _analyze_chain(rows)
    except Exception:
        return {}

def _from_yahoo(symbol):
    try:
        t = yf.Ticker(symbol)
        expirations = t.options
        if not expirations:
            return {}
        exp = expirations[0]
        chain = t.option_chain(exp)
        rows = []
        for _, r in chain.calls.iterrows():
            rows.append({"strike": float(r["strike"]), "type": "call", "volume": int(r.get("volume", 0) or 0), "openInterest": int(r.get("openInterest", 0) or 0), "iv": float(r.get("impliedVolatility", 0) or 0), "gamma": 0.0})
        for _, r in chain.puts.iterrows():
            rows.append({"strike": float(r["strike"]), "type": "put", "volume": int(r.get("volume", 0) or 0), "openInterest": int(r.get("openInterest", 0) or 0), "iv": float(r.get("impliedVolatility", 0) or 0), "gamma": 0.0})
        return _analyze_chain(rows)
    except Exception:
        return {}

def _analyze_chain(rows):
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    if df.empty:
        return {}

    strikes = sorted(df["strike"].dropna().unique())
    if not strikes:
        return {}

    call_df = df[df["type"].str.lower().eq("call")]
    put_df = df[df["type"].str.lower().eq("put")]

    call_wall = None if call_df.empty else float(call_df.groupby("strike")["openInterest"].sum().idxmax())
    put_wall = None if put_df.empty else float(put_df.groupby("strike")["openInterest"].sum().idxmax())

    max_pain = _calc_max_pain(df, strikes)

    # GEX בסיסי: gamma * OI, calls positive, puts negative
    gex = 0.0
    for _, r in df.iterrows():
        sign = 1 if str(r["type"]).lower() == "call" else -1
        gex += sign * float(r.get("gamma", 0) or 0) * float(r.get("openInterest", 0) or 0)
    gex_bias = "חיובי/מייצב" if gex > 0 else "שלילי/תנודתי" if gex < 0 else "לא זמין"

    pivot = df.pivot_table(index="strike", columns="type", values=["volume", "openInterest"], aggfunc="sum", fill_value=0)
    table = []
    for strike in strikes:
        call_vol = int(pivot.loc[strike].get(("volume","call"), 0)) if strike in pivot.index else 0
        put_vol = int(pivot.loc[strike].get(("volume","put"), 0)) if strike in pivot.index else 0
        call_oi = int(pivot.loc[strike].get(("openInterest","call"), 0)) if strike in pivot.index else 0
        put_oi = int(pivot.loc[strike].get(("openInterest","put"), 0)) if strike in pivot.index else 0
        if call_oi + put_oi + call_vol + put_vol > 0:
            table.append({"Strike": strike, "Call OI": call_oi, "Put OI": put_oi, "Call Vol": call_vol, "Put Vol": put_vol})
    table = sorted(table, key=lambda x: x["Call OI"] + x["Put OI"] + x["Call Vol"] + x["Put Vol"], reverse=True)[:30]

    call_vol_sum = int(call_df["volume"].sum()) if not call_df.empty else 0
    put_vol_sum = int(put_df["volume"].sum()) if not put_df.empty else 0
    pcr = round(put_vol_sum / call_vol_sum, 2) if call_vol_sum else None

    return {
        "chain_table": table,
        "max_pain": max_pain,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "gex_bias": gex_bias,
        "gex_raw": round(gex, 4),
        "put_call_volume_ratio": pcr,
        "call_volume": call_vol_sum,
        "put_volume": put_vol_sum,
    }

def _calc_max_pain(df, strikes):
    min_pain = None
    best = None
    for s in strikes:
        pain = 0.0
        for _, r in df.iterrows():
            oi = float(r.get("openInterest", 0) or 0)
            k = float(r["strike"])
            if str(r["type"]).lower() == "call":
                pain += max(0, s - k) * oi
            else:
                pain += max(0, k - s) * oi
        if min_pain is None or pain < min_pain:
            min_pain = pain
            best = s
    return float(best) if best is not None else None
