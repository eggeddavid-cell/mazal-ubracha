import math
import numpy as np
import pandas as pd

def _score_row(row):
    score=50; checks=[]
    def add(name,cond,w):
        nonlocal score
        score += w if cond else -w
        checks.append({"בדיקה":name,"תוצאה":"חיובי" if cond else "שלילי","משקל":w})
    add("מחיר מעל VWAP", row["Close"]>row["VWAP"], 9)
    add("EMA9 מעל EMA20", row["EMA9"]>row["EMA20"], 7)
    add("EMA20 מעל EMA50", row["EMA20"]>row["EMA50"], 7)
    add("מחיר מעל EMA200", row["Close"]>row["EMA200"], 6)
    add("MACD Histogram חיובי", row["MACD_Hist"]>0, 7)
    add("RSI מעל 50", row["RSI"]>50, 6)
    add("RSI לא בקיצון", 25<row["RSI"]<75, 4)
    add("Stochastic תומך", row["Stoch_K"]>row["Stoch_D"], 4)
    add("ADX מגמה פעילה", row["ADX"]>18, 4)
    add("+DI מעל -DI", row["Plus_DI"]>row["Minus_DI"], 5)
    add("Volume מעל ממוצע", row["Volume_Ratio"]>1, 6)
    add("OBV מעל ממוצע", row["OBV"]>row["OBV_EMA"], 5)
    add("תשואה 5 נרות חיובית", row["Return_5"]>0, 5)
    add("לא צמוד מדי לבנד עליון", row["Close"]<row["BB_Upper"]*1.005, 3)
    return max(0,min(100,int(score))), checks

def _sigmoid(score): return 1/(1+math.exp(-(score-50)/10))

def _eval_trade(df,i,action,h):
    entry=float(df["Close"].iloc[i]); atr=float(df["ATR"].iloc[i])
    if atr<=0 or np.isnan(atr): return None
    fut=df.iloc[i+1:i+1+h]
    if len(fut)<h: return None
    if action=="CALL":
        stop=entry-1.1*atr; target=entry+1.5*atr
        for _,r in fut.iterrows():
            if r["Low"]<=stop: return 0
            if r["High"]>=target: return 1
        return int(float(fut["Close"].iloc[-1])>entry)
    if action=="PUT":
        stop=entry+1.1*atr; target=entry-1.5*atr
        for _,r in fut.iterrows():
            if r["High"]>=stop: return 0
            if r["Low"]<=target: return 1
        return int(float(fut["Close"].iloc[-1])<entry)
    return None

def run_backtest(df,horizon=8):
    rows=[]; start=60; end=len(df)-horizon-1
    if end<=start: return {"sample":0,"win_rate":None,"call_win":None,"put_win":None,"expectancy":None}, []
    for i in range(start,end):
        score,_=_score_row(df.iloc[i])
        action="CALL" if score>=68 else "PUT" if score<=35 else None
        if not action: continue
        win=_eval_trade(df,i,action,horizon)
        if win is None: continue
        rows.append({"זמן":str(df.index[i]),"פעולה":action,"ציון":score,"תוצאה":"ניצחון" if win else "הפסד","win":win})
    if not rows: return {"sample":0,"win_rate":None,"call_win":None,"put_win":None,"expectancy":None}, []
    hist=pd.DataFrame(rows); wr=round(float(hist["win"].mean()*100),1)
    call=hist[hist["פעולה"]=="CALL"]; put=hist[hist["פעולה"]=="PUT"]
    call_wr=round(float(call["win"].mean()*100),1) if len(call) else None
    put_wr=round(float(put["win"].mean()*100),1) if len(put) else None
    exp=round((wr/100)*1.5-(1-wr/100)*1.1,3)
    return {"מספר עסקאות במדגם":int(len(hist)),"אחוז הצלחה כללי":wr,"אחוז הצלחה CALL":call_wr,"אחוז הצלחה PUT":put_wr,"תוחלת R משוערת":exp,"sample":int(len(hist)),"win_rate":wr,"call_win":call_wr,"put_win":put_wr,"expectancy":exp}, rows

def analyze_symbol(symbol,df,levels,patterns,horizon,account_size,risk_pct):
    last=df.iloc[-1]; score,checks=_score_row(last); bt,bt_rows=run_backtest(df,horizon)
    model_prob=_sigmoid(score)*100; sample=bt.get("sample",0); bt_wr=bt.get("win_rate")
    if bt_wr is not None and sample>=10:
        w=min(0.45,sample/100); prob_up=model_prob*(1-w)+bt_wr*w
    else: prob_up=model_prob
    ptxt=" ".join([p.get("כיוון","")+" "+p.get("תבנית","") for p in patterns])
    if "שורית" in ptxt: prob_up+=3; score+=3; checks.append({"בדיקה":"תבנית נרות שורית","תוצאה":"חיובי","משקל":3})
    if "דובית" in ptxt: prob_up-=3; score-=3; checks.append({"בדיקה":"תבנית נרות דובית","תוצאה":"שלילי","משקל":3})
    prob_up=max(5,min(95,round(prob_up,1))); prob_down=round(100-prob_up,1)
    if prob_up>=62 and score>=64: action="CALL"; bias="שורית"
    elif prob_down>=62 and score<=40: action="PUT"; bias="דובית"
    else: action="WAIT"; bias="ניטרלית"
    conf=45+min(25,sample*0.5)+(10 if abs(prob_up-50)>=12 else 0)+(10 if abs(score-50)>=15 else 0)+(5 if bt.get("expectancy") is not None and bt.get("expectancy")>0 else 0)
    conf=int(max(35,min(95,conf)))
    entry=float(last["Close"]); atr=float(last["ATR"]); support=float(levels["support"]); resistance=float(levels["resistance"])
    if action=="CALL": stop=max(support,entry-1.1*atr); target1=entry+1.5*atr; target2=entry+2.4*atr
    elif action=="PUT": stop=min(resistance,entry+1.1*atr); target1=entry-1.5*atr; target2=entry-2.4*atr
    else: stop=support if entry>support else entry-1.1*atr; target1=resistance if resistance>entry else entry+1.5*atr; target2=target1+0.9*atr
    risk_dollars=account_size*risk_pct/100; unit_risk=abs(entry-stop); units=int(risk_dollars/unit_risk) if unit_risk>0 else 0; rr=abs(target1-entry)/unit_risk if unit_risk>0 else None
    trade={"פעולה":action,"כיוון":bias,"כניסה":round(entry,2),"סטופ":round(stop,2),"יעד 1":round(target1,2),"יעד 2":round(target2,2),"יחס סיכון/סיכוי":round(rr,2) if rr else None,"הסתברות Up":f"{prob_up}%","אמינות":f"{conf}%"}
    risk_plan={"גודל חשבון":account_size,"סיכון לעסקה %":risk_pct,"סיכון מקסימלי $":round(risk_dollars,2),"סיכון ליחידה":round(unit_risk,2),"כמות יחידות משוערת":units,"ATR":round(atr,3)}
    latest={"Close":round(entry,2),"VWAP":round(float(last["VWAP"]),2),"EMA20":round(float(last["EMA20"]),2),"EMA50":round(float(last["EMA50"]),2),"EMA200":round(float(last["EMA200"]),2),"RSI":round(float(last["RSI"]),2),"MACD Hist":round(float(last["MACD_Hist"]),4),"ADX":round(float(last["ADX"]),2),"Volume Ratio":round(float(last["Volume_Ratio"]),2),"ATR":round(atr,3)}
    summary=f"{symbol}: פעולה {action}, מגמה {bias}, ציון {int(max(0,min(100,score)))}/100, הסתברות Up {prob_up}%, אמינות {conf}%. מחיר {entry:.2f}, VWAP {last['VWAP']:.2f}, תמיכה {support:.2f}, התנגדות {resistance:.2f}. Backtest: {sample} עסקאות, הצלחה {bt.get('win_rate')}%, תוחלת {bt.get('expectancy')}R."
    return {"symbol":symbol,"action":action,"bias":bias,"score":int(max(0,min(100,score))),"prob_up":prob_up,"prob_down":prob_down,"confidence":conf,"last_close":entry,"summary":summary,"trade_plan":trade,"risk_plan":risk_plan,"checks":checks,"latest_indicators":latest,"backtest_summary":bt,"backtest_trades":bt_rows}
