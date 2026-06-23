import pandas as pd

def analyze_options_chain(chain, spot):
    if not chain or not chain.get("available"):
        return {"available": False}
    calls = chain["calls"].copy(); puts = chain["puts"].copy(); exp = chain.get("expiration")
    for df in (calls, puts):
        for col in ["volume", "openInterest", "strike", "impliedVolatility"]:
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    call_vol = int(calls["volume"].sum()); put_vol = int(puts["volume"].sum())
    call_oi = int(calls["openInterest"].sum()); put_oi = int(puts["openInterest"].sum())
    pcr_vol = round(put_vol / call_vol, 2) if call_vol else None
    pcr_oi = round(put_oi / call_oi, 2) if call_oi else None
    strikes = sorted(set(calls["strike"]).intersection(set(puts["strike"])))
    max_pain = None; min_pain = None
    for s in strikes:
        pain = sum(max(0, s-k)*oi for k, oi in zip(calls["strike"], calls["openInterest"])) + sum(max(0, k-s)*oi for k, oi in zip(puts["strike"], puts["openInterest"]))
        if min_pain is None or pain < min_pain:
            min_pain = pain; max_pain = s
    walls = []
    for _, r in calls.sort_values("openInterest", ascending=False).head(3)[["strike", "openInterest", "volume"]].iterrows():
        walls.append({"סוג": "Call Wall", "סטרייק": r["strike"], "OI": int(r["openInterest"]), "Volume": int(r["volume"])})
    for _, r in puts.sort_values("openInterest", ascending=False).head(3)[["strike", "openInterest", "volume"]].iterrows():
        walls.append({"סוג": "Put Wall", "סטרייק": r["strike"], "OI": int(r["openInterest"]), "Volume": int(r["volume"])})
    merged = pd.merge(calls[["strike","openInterest","volume"]], puts[["strike","openInterest","volume"]], on="strike", how="outer", suffixes=("_call","_put")).fillna(0)
    near = merged[(merged["strike"] >= spot*0.9) & (merged["strike"] <= spot*1.1)].sort_values("strike")
    heat = [{"Strike": r["strike"], "Call OI": int(r["openInterest_call"]), "Put OI": int(r["openInterest_put"]), "Call Vol": int(r["volume_call"]), "Put Vol": int(r["volume_put"])} for _, r in near.iterrows()]
    bias = "שורי" if (pcr_vol is not None and pcr_vol < 0.8) else "דובי" if (pcr_vol is not None and pcr_vol > 1.2) else "ניטרלי"
    return {"available": True, "expiration": exp, "put_call_volume_ratio": pcr_vol, "put_call_oi_ratio": pcr_oi, "call_volume": call_vol, "put_volume": put_vol, "call_oi": call_oi, "put_oi": put_oi, "max_pain": round(float(max_pain),2) if max_pain else None, "bias": bias, "walls": walls, "heatmap": heat[:40]}
