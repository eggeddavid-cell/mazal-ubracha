import math
import pandas as pd
from data import get_market_data
from indicators import add_indicators, detect_levels, detect_patterns

def _components(row):
    trend = (5 if row['Close'] > row['EMA20'] else 0) + (5 if row['EMA20'] > row['EMA50'] else 0) + (8 if row['EMA50'] > row['EMA200'] else 0) + (7 if row['ADX'] > 22 else 0)
    momentum = (8 if row['RSI'] > 50 else 0) + (6 if row['MACD_Hist'] > 0 else 0) + (6 if row['Stoch_K'] > row['Stoch_D'] else 0)
    volume = (10 if row['Volume_Ratio'] > 1.2 else 5 if row['Volume_Ratio'] > 1 else 0) + (5 if row['OBV'] > row['OBV_EMA'] else 0)
    volatility = (8 if row['ATR'] > row['ATR_MA'] else 0) + (7 if row['Close'] > row['BB_Upper'] or row['Close'] < row['BB_Lower'] else 3)
    price_action = (8 if row['Close'] > row['VWAP'] else 0) + (7 if row['Return_5'] > 0 else 0)
    return {'Trend':trend,'Momentum':momentum,'Volume':volume,'Volatility':volatility,'Price Action':price_action}

def _direction_score(row):
    score=50; checks=[]
    def add(n,c,w):
        nonlocal score
        score += w if c else -w
        checks.append({'בדיקה':n,'תוצאה':'חיובי' if c else 'שלילי','משקל':w})
    add('מחיר מעל VWAP', row['Close'] > row['VWAP'], 9)
    add('EMA20 מעל EMA50', row['EMA20'] > row['EMA50'], 8)
    add('מחיר מעל EMA200', row['Close'] > row['EMA200'], 7)
    add('MACD חיובי', row['MACD_Hist'] > 0, 7)
    add('RSI מעל 50', row['RSI'] > 50, 6)
    add('+DI מעל -DI', row['Plus_DI'] > row['Minus_DI'], 5)
    add('Volume מעל ממוצע', row['Volume_Ratio'] > 1, 6)
    add('OBV מעל ממוצע', row['OBV'] > row['OBV_EMA'], 5)
    add('תשואה 5 נרות חיובית', row['Return_5'] > 0, 5)
    return max(0,min(100,int(score))), checks

def _prob(score): return 100/(1+math.exp(-(score-50)/10))

def run_backtest(df, horizon=8):
    trades=[]
    for i in range(60, len(df)-horizon-1):
        score,_ = _direction_score(df.iloc[i])
        action = 'CALL' if score >= 68 else 'PUT' if score <= 35 else 'WAIT'
        if action == 'WAIT': continue
        entry=float(df['Close'].iloc[i]); atr=float(df['ATR'].iloc[i]); future=df.iloc[i+1:i+1+horizon]
        if action=='CALL': win=0 if any(future['Low']<=entry-1.1*atr) else int(any(future['High']>=entry+1.5*atr))
        else: win=0 if any(future['High']>=entry+1.1*atr) else int(any(future['Low']<=entry-1.5*atr))
        trades.append({'זמן':str(df.index[i]),'פעולה':action,'ציון':score,'תוצאה':'ניצחון' if win else 'הפסד','win':win})
    if not trades: return {'עסקאות במדגם':0,'אחוז הצלחה':None,'תוחלת R':None}, []
    h=pd.DataFrame(trades); wr=float(h['win'].mean()*100); exp=(wr/100)*1.5-(1-wr/100)*1.1
    return {'עסקאות במדגם':len(trades),'אחוז הצלחה':round(wr,1),'תוחלת R':round(exp,3)}, trades

def analyze_symbol(symbol, df, levels, patterns, tf_data, horizon, account_size, risk_pct):
    last=df.iloc[-1]; dscore, checks = _direction_score(last); comps=_components(last); raw_quality=sum(comps.values())
    bt,trades=run_backtest(df,horizon); sample=bt.get('עסקאות במדגם',0); wr=bt.get('אחוז הצלחה')
    mtf=[]; mtf_score=0
    for name,tdf in tf_data.items():
        s,_=_direction_score(tdf.iloc[-1]); d='CALL' if s>=65 else 'PUT' if s<=38 else 'WAIT'
        mtf.append({'טיים פריים':name,'כיוון':d,'ציון':s}); mtf_score += 5 if d=='CALL' else -5 if d=='PUT' else 0
    ptxt=' '.join([p.get('כיוון','') for p in patterns]); pattern_bonus = 4 if 'שורית' in ptxt else -4 if 'דובית' in ptxt else 0
    call_prob=_prob(dscore)+mtf_score+pattern_bonus
    if wr is not None and sample>=10:
        w=min(0.35, sample/100); call_prob=call_prob*(1-w)+(wr if dscore>=50 else 100-wr)*w
    call_prob=round(max(5,min(95,call_prob)),1); put_prob=round(max(5,min(95,100-call_prob)),1); wait_prob=round(max(0,100-max(call_prob,put_prob)),1)
    action='STRONG CALL' if call_prob>=78 else 'CALL' if call_prob>=63 else 'STRONG PUT' if put_prob>=78 else 'PUT' if put_prob>=63 else 'WAIT'
    quality=int(max(0,min(100, raw_quality+(10 if sample>=10 and wr and wr>55 else 0)+abs(mtf_score))))
    confidence=int(max(35,min(95,45+min(20,sample*0.4)+(10 if abs(call_prob-50)>=15 else 0)+(10 if quality>=75 else 0))))
    grade='A+' if quality>=88 and confidence>=75 else 'A' if quality>=78 else 'B' if quality>=68 else 'C' if quality>=55 else 'D'
    entry=float(last['Close']); atr=float(last['ATR']); support=float(levels['support']); resistance=float(levels['resistance'])
    if 'CALL' in action: stop,t1,t2=max(support,entry-1.1*atr), entry+1.5*atr, entry+2.4*atr
    elif 'PUT' in action: stop,t1,t2=min(resistance,entry+1.1*atr), entry-1.5*atr, entry-2.4*atr
    else: stop,t1,t2=support,resistance,resistance+atr
    unit_r=abs(entry-stop); rr=abs(t1-entry)/unit_r if unit_r else 0; risk_d=account_size*risk_pct/100; units=int(risk_d/unit_r) if unit_r>0 else 0
    risk_label='LOW' if rr>=2.2 and float(last['Volume_Ratio'])<2.5 else 'MEDIUM' if rr>=1.5 else 'HIGH'
    trade={'פעולה':action,'Grade':grade,'כניסה':round(entry,2),'סטופ':round(stop,2),'יעד 1':round(t1,2),'יעד 2':round(t2,2),'יחס סיכון/סיכוי':round(rr,2),'CALL %':call_prob,'PUT %':put_prob,'WAIT %':wait_prob,'Risk':risk_label}
    risk={'גודל חשבון':account_size,'סיכון %':risk_pct,'סיכון $':round(risk_d,2),'סיכון ליחידה':round(unit_r,2),'כמות יחידות':units,'ATR':round(atr,3),'Risk':risk_label}
    latest={'Close':round(entry,2),'VWAP':round(float(last['VWAP']),2),'EMA20':round(float(last['EMA20']),2),'EMA50':round(float(last['EMA50']),2),'EMA200':round(float(last['EMA200']),2),'RSI':round(float(last['RSI']),2),'MACD Hist':round(float(last['MACD_Hist']),4),'ADX':round(float(last['ADX']),2),'Volume Ratio':round(float(last['Volume_Ratio']),2),'ATR':round(atr,3)}
    flow={**comps,'Multi TF Bonus':mtf_score,'Pattern Bonus':pattern_bonus,'Quality Score':quality,'Setup Grade':grade}
    breakdown=[{'רכיב':k,'ציון':v} for k,v in comps.items()]+[{'רכיב':'Multi-Timeframe','ציון':mtf_score},{'רכיב':'Pattern','ציון':pattern_bonus},{'רכיב':'Quality Total','ציון':quality}]
    summary=f"{symbol}: {action}, Grade {grade}, איכות {quality}/100, CALL {call_prob}%, PUT {put_prob}%, אמינות {confidence}%. Risk {risk_label}. Backtest: {sample} עסקאות, הצלחה {wr}%."
    return {'action':action,'grade':grade,'call_prob':call_prob,'put_prob':put_prob,'wait_prob':wait_prob,'confidence':confidence,'quality_score':quality,'risk_label':risk_label,'last_close':entry,'summary':summary,'trade_plan':trade,'risk_plan':risk,'latest_indicators':latest,'score_breakdown':breakdown,'multi_timeframe':mtf,'backtest_summary':bt,'backtest_trades':trades,'flow_analysis':flow}

def scan_symbols(symbols, interval='15min', horizon=8):
    rows=[]
    for sym in symbols:
        try:
            df,src,err=get_market_data(sym, interval=interval)
            if err or df.empty: continue
            df=add_indicators(df)
            if len(df)<80: continue
            res=analyze_symbol(sym, df, detect_levels(df), detect_patterns(df), {}, horizon, 10000, 1)
            rows.append({'סימול':sym,'פעולה':res['action'],'Grade':res['grade'],'ציון איכות':res['quality_score'],'CALL %':res['call_prob'],'PUT %':res['put_prob'],'Risk':res['risk_label'],'מחיר':round(res['last_close'],2),'מקור':src})
        except Exception: continue
    if not rows: return pd.DataFrame()
    df=pd.DataFrame(rows); rank={'A+':5,'A':4,'B':3,'C':2,'D':1}; df['_rank']=df['Grade'].map(rank).fillna(0)
    return df.sort_values(['_rank','ציון איכות'], ascending=False).drop(columns=['_rank'])
