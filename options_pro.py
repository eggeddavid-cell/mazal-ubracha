import streamlit as st
import requests
import pandas as pd
import math

def _get_secret(name):
    try:
        return st.secrets.get(name, None)
    except Exception:
        return None

@st.cache_data(ttl=900, show_spinner=False)
def get_options_pro(symbol: str, spot_price: float):
    key = _get_secret("FMP_API_KEY")
    if not key:
        return {"source": "none", "chain_table": []}

    chain = _try_fmp_endpoints(symbol, key)
    if not chain:
        return {"source": "none", "chain_table": []}

    rows = _normalize_chain(chain)
    if not rows:
        return {"source": "none", "chain_table": []}

    analysis = _analyze(rows, spot_price)
    analysis["source"] = "FMP"
    return analysis

def _try_fmp_endpoints(symbol, key):
    urls = [
        f"https://financialmodelingprep.com/stable/options-chain?symbol={symbol}&apikey={key}",
        f"https://financialmodelingprep.com/api/v3/options-chain/{symbol}?apikey={key}",
        f"https://financialmodelingprep.com/api/v4/options-chain?symbol={symbol}&apikey={key}",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                continue
            data = r.json()
            if isinstance(data, dict):
                for k in ["data", "options", "optionChain", "results"]:
                    if isinstance(data.get(k), list) and data.get(k):
                        return data.get(k)
                if data:
                    # sometimes dict contains date keys
                    vals = []
                    for v in data.values():
                        if isinstance(v, list):
                            vals += v
                    if vals:
                        return vals
            if isinstance(data, list) and data:
                return data
        except Exception:
            continue
    return []

def _pick(d, keys, default=None):
    for k in keys:
        if k in d and d.get(k) not in [None, "", "null"]:
            return d.get(k)
    return default

def _to_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

def _to_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except Exception:
        return default

def _normalize_chain(items):
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue

        # FMP can return either separated call/put fields or one row per contract.
        opt_type = str(_pick(it, ["type", "optionType", "contractType", "side"], "")).lower()
        strike = _to_float(_pick(it, ["strike", "strikePrice", "strike_price", "exercisePrice"], 0))

        if not opt_type and ("callOpenInterest" in it or "putOpenInterest" in it):
            call_oi = _to_int(_pick(it, ["callOpenInterest", "callOI", "call_oi"], 0))
            put_oi = _to_int(_pick(it, ["putOpenInterest", "putOI", "put_oi"], 0))
            call_vol = _to_int(_pick(it, ["callVolume", "callVol", "call_volume"], 0))
            put_vol = _to_int(_pick(it, ["putVolume", "putVol", "put_volume"], 0))
            call_gamma = _to_float(_pick(it, ["callGamma", "gammaCall"], 0))
            put_gamma = _to_float(_pick(it, ["putGamma", "gammaPut"], 0))
            if strike:
                rows.append({"strike": strike, "type": "call", "openInterest": call_oi, "volume": call_vol, "gamma": call_gamma})
                rows.append({"strike": strike, "type": "put", "openInterest": put_oi, "volume": put_vol, "gamma": put_gamma})
            continue

        if "call" in opt_type:
            typ = "call"
        elif "put" in opt_type:
            typ = "put"
        else:
            symbol = str(_pick(it, ["symbol", "contractSymbol", "optionSymbol"], "")).lower()
            typ = "call" if "c" in symbol[-9:] else "put" if "p" in symbol[-9:] else ""

        oi = _to_int(_pick(it, ["openInterest", "open_interest", "oi"], 0))
        vol = _to_int(_pick(it, ["volume", "vol"], 0))
        gamma = _to_float(_pick(it, ["gamma"], 0))
        if strike and typ in ["call", "put"]:
            rows.append({"strike": strike, "type": typ, "openInterest": oi, "volume": vol, "gamma": gamma})
    return rows

def _analyze(rows, spot):
    df = pd.DataFrame(rows)
    if df.empty:
        return {"chain_table": []}

    call_df = df[df["type"] == "call"]
    put_df = df[df["type"] == "put"]

    call_wall = None if call_df.empty else float(call_df.groupby("strike")["openInterest"].sum().idxmax())
    put_wall = None if put_df.empty else float(put_df.groupby("strike")["openInterest"].sum().idxmax())
    max_pain = _max_pain(df)

    call_oi = int(call_df["openInterest"].sum()) if not call_df.empty else 0
    put_oi = int(put_df["openInterest"].sum()) if not put_df.empty else 0
    call_vol = int(call_df["volume"].sum()) if not call_df.empty else 0
    put_vol = int(put_df["volume"].sum()) if not put_df.empty else 0

    pcr_oi = round(put_oi / call_oi, 2) if call_oi else None
    pcr_vol = round(put_vol / call_vol, 2) if call_vol else None

    # GEX proxy: true GEX needs multiplier and spot^2 and gamma; if gamma unavailable, use OI wall proxy.
    gex_raw = 0.0
    if "gamma" in df and df["gamma"].abs().sum() > 0:
        for _, r in df.iterrows():
            sign = 1 if r["type"] == "call" else -1
            gex_raw += sign * float(r["gamma"]) * float(r["openInterest"])
        gex_bias = "חיובי/מייצב" if gex_raw > 0 else "שלילי/תנודתי" if gex_raw < 0 else "ניטרלי"
    else:
        gex_raw = call_oi - put_oi
        gex_bias = "חיובי/מייצב" if gex_raw > 0 else "שלילי/תנודתי" if gex_raw < 0 else "ניטרלי"

    options_bias = "Bullish" if (pcr_oi is not None and pcr_oi < 0.85) else "Bearish" if (pcr_oi is not None and pcr_oi > 1.15) else "Neutral"

    pivot = df.pivot_table(index="strike", columns="type", values=["openInterest","volume"], aggfunc="sum", fill_value=0)
    table = []
    for strike in pivot.index:
        def val(a,b):
            try: return int(pivot.loc[strike][(a,b)])
            except Exception: return 0
        coi, poi = val("openInterest","call"), val("openInterest","put")
        cv, pv = val("volume","call"), val("volume","put")
        total = coi + poi + cv + pv
        if total > 0:
            table.append({"Strike": float(strike), "Call OI": coi, "Put OI": poi, "Call Vol": cv, "Put Vol": pv, "Total": total})
    table = sorted(table, key=lambda x: x["Total"], reverse=True)[:40]

    return {
        "chain_table": table,
        "max_pain": round(max_pain, 2) if max_pain else None,
        "call_wall": round(call_wall, 2) if call_wall else None,
        "put_wall": round(put_wall, 2) if put_wall else None,
        "put_call_oi_ratio": pcr_oi,
        "put_call_volume_ratio": pcr_vol,
        "call_open_interest": call_oi,
        "put_open_interest": put_oi,
        "call_volume": call_vol,
        "put_volume": put_vol,
        "gex_proxy": gex_bias,
        "gex_raw": round(float(gex_raw), 4),
        "options_bias": options_bias,
    }

def _max_pain(df):
    strikes = sorted(df["strike"].dropna().unique())
    if not strikes:
        return None
    best = None
    best_pain = None
    for s in strikes:
        pain = 0.0
        for _, r in df.iterrows():
            k = float(r["strike"])
            oi = float(r["openInterest"])
            if r["type"] == "call":
                pain += max(0, s-k) * oi
            else:
                pain += max(0, k-s) * oi
        if best_pain is None or pain < best_pain:
            best_pain = pain
            best = s
    return float(best) if best is not None else None
