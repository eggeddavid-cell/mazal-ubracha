import math
import pandas as pd

def _score(row):
    score = 50; checks = []
    def add(name, cond, w):
        nonlocal score
        score += w if cond else -w
        checks.append({"בדיקה":name,"תוצאה":"חיובי" if cond else "שלילי","משקל":w})
    add("מחיר מעל VWAP", row["Close"] > row["VWAP"], 9)
    add("EMA9 מעל EMA20", row["EMA9"] > row["EMA20"], 7)
    add("EMA20 מעל EMA50", row["EMA20"] > row["EMA50"], 7)
    add("מחיר מעל EMA200", row["Close"] > row["EMA200"], 6)
    add("MACD חיובי", row["MACD_Hist"] > 0, 7)
    add("RSI מעל 50", row["RSI"] > 50, 6)
    add("RSI לא בקיצון", 25 < row["RSI"] < 75, 4)
    add("Stochastic תומך", row["Stoch_K"] > row["Stoch_D"], 4)
    add("ADX מגמה פעילה", row["ADX"] > 18, 4)
    add("+DI מעל -DI", row["Plus_DI"] > row["Minus_DI"], 5)
    add("Volume מעל ממוצע", row["Volume_Ratio"] > 1, 6)
    add("OBV מעל ממוצע", row["OBV"] > row["OBV_EMA"], 5)
    add("תשואה 5 נרות חיובית", row["Return_5"] > 0, 5)
    return max(0, min(100, int(score))), checks

def _prob(score): return 100/(1+math.exp(-(score-50)/10))

def run_backtest(df, horizon=8):
    trades = []
    for i in range(60, len(df)-horizon-1):
        score, _ = _score(df.iloc[i])
        action = "CALL" if score >= 68 else "PUT" if score <= 35 else "WAIT"
        if action == "WAIT": continue
        entry = float(df["Close"].iloc[i]); atr = float(df["ATR"].iloc[i]); future = df.iloc[i+1:i+1+horizon]
        if action == "CALL":
            win = 0 if any(future["Low"] <= entry-1.1*atr) else int(any(future["High"] >= entry+1.5*atr))
        else:
            win = 0 if any(future["High"] >= entry+1.1*atr) else int(any(future["Low"] <= entry-1.5*atr))
        trades.append({"זמן":str(df.index[i]),"פעולה":action,"ציון":score,"תוצאה":"ניצחון" if win else "הפסד","win":win})
    if not trades: return {"עסקאות במדגם":0,"אחוז הצלחה":None,"תוחלת R":None}, []
    h = pd.DataFrame(trades); wr = float(h["win"].mean()*100); exp = (wr/100)*1.5 - (1-wr/100)*1.1
    return {"עסקאות במדגם":len(trades),"אחוז הצלחה":round(wr,1),"תוחלת R":round(exp,3)}, trades

def analyze_symbol(symbol, df, levels, patterns, tf_data, horizon, account_size, risk_pct):
    last = df.iloc[-1]; score, checks = _score(last)
    bt, trades = run_backtest(df, horizon)
    call_prob = _prob(score)
    sample, wr = bt.get("עסקאות במדגם",0), bt.get("אחוז הצלחה")
    if wr is not None and sample >= 10:
        w = min(0.40, sample/100)
        call_prob = call_prob*(1-w) + (wr if score >= 50 else 100-wr)*w
    mtf = []
    for name, tdf in tf_data.items():
        s, _ = _score(tdf.iloc[-1]); d = "CALL" if s >= 65 else "PUT" if s <= 38 else "WAIT"
        mtf.append({"טיים פריים":name,"כיוון":d,"ציון":s})
        call_prob += 3 if d=="CALL" else -3 if d=="PUT" else 0
    text = " ".join([p.get("כיוון","") for p in patterns])
    if "שורית" in text: call_prob += 3
    if "דובית" in text: call_prob -= 3
    call_prob = round(max(5, min(95, call_prob)), 1)
    put_prob = round(max(5, min(95, 100-call_prob)), 1)
    wait_prob = round(max(0, 100-max(call_prob, put_prob)), 1)
    action = "STRONG CALL" if call_prob >= 78 else "CALL" if call_prob >= 63 else "STRONG PUT" if put_prob >= 78 else "PUT" if put_prob >= 63 else "WAIT"
    confidence = int(max(35, min(95, 45 + min(25, sample*0.5) + (10 if abs(call_prob-50)>=15 else 0) + (10 if abs(score-50)>=15 else 0))))
    grade_score = confidence*.45 + max(call_prob,put_prob)*.35 + (score if "CALL" in action else 100-score if "PUT" in action else 50)*.20
    grade = "A+" if grade_score>=88 else "A" if grade_score>=78 else "B" if grade_score>=68 else "C" if grade_score>=55 else "D"
    entry = float(last["Close"]); atr = float(last["ATR"]); support, resistance = float(levels["support"]), float(levels["resistance"])
    if "CALL" in action: stop, t1, t2 = max(support, entry-1.1*atr), entry+1.5*atr, entry+2.4*atr
    elif "PUT" in action: stop, t1, t2 = min(resistance, entry+1.1*atr), entry-1.5*atr, entry-2.4*atr
    else: stop, t1, t2 = support, resistance, resistance+atr
    risk_d = account_size*risk_pct/100; unit_r = abs(entry-stop); units = int(risk_d/unit_r) if unit_r>0 else 0
    trade_plan = {"פעולה":action,"Grade":grade,"כניסה":round(entry,2),"סטופ":round(stop,2),"יעד 1":round(t1,2),"יעד 2":round(t2,2),"יחס סיכון/סיכוי":round(abs(t1-entry)/unit_r,2) if unit_r else None,"CALL %":call_prob,"PUT %":put_prob,"WAIT %":wait_prob}
    risk_plan = {"גודל חשבון":account_size,"סיכון %":risk_pct,"סיכון $":round(risk_d,2),"סיכון ליחידה":round(unit_r,2),"כמות יחידות":units,"ATR":round(atr,3)}
    latest = {"Close":round(entry,2),"VWAP":round(float(last["VWAP"]),2),"EMA20":round(float(last["EMA20"]),2),"EMA50":round(float(last["EMA50"]),2),"EMA200":round(float(last["EMA200"]),2),"RSI":round(float(last["RSI"]),2),"MACD Hist":round(float(last["MACD_Hist"]),4),"ADX":round(float(last["ADX"]),2),"Volume Ratio":round(float(last["Volume_Ratio"]),2),"ATR":round(atr,3)}
    summary = f"{symbol}: {action}, Grade {grade}, CALL {call_prob}%, PUT {put_prob}%, אמינות {confidence}%. ציון מנוע {score}/100. Backtest: {sample} עסקאות, הצלחה {wr}%."
    return {"action":action,"grade":grade,"call_prob":call_prob,"put_prob":put_prob,"wait_prob":wait_prob,"confidence":confidence,"score":score,"last_close":entry,"summary":summary,"trade_plan":trade_plan,"risk_plan":risk_plan,"latest_indicators":latest,"checks":checks,"multi_timeframe":mtf,"backtest_summary":bt,"backtest_trades":trades}
