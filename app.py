import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data import get_stock_history, get_news
from indicators import add_indicators, detect_patterns, detect_levels
from engine import analyze_symbol
from pdf_report import create_pdf_report

st.set_page_config(page_title="Options Daily Trend AI v7 Quant", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
h1,h2,h3,h4,h5,h6,p,label { text-align: right; }
div[data-testid="stMetric"] { text-align:center;background:#f8fafc;padding:14px;border-radius:14px;border:1px solid #e5e7eb; }
.big-title { font-size:38px;font-weight:950;margin-bottom:4px; }
.small-muted { color:#64748b;font-size:14px; }
.signal-box { padding:24px;border-radius:20px;color:white;font-size:32px;font-weight:950;text-align:center; }
.score-box { padding:24px;border-radius:20px;background:#0f172a;color:white;text-align:center; }
.score-number { font-size:52px;font-weight:950; }
.note { background:#eef6ff;border:1px solid #bfdbfe;padding:14px;border-radius:12px; }
.warn { background:#fff7ed;border:1px solid #fed7aa;padding:14px;border-radius:12px; }
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="big-title">Options Daily Trend AI v7 Quant</div>', unsafe_allow_html=True)
st.markdown('<div class="small-muted">מערכת Price Action + אינדיקטורים + Backtest פנימי + הסתברות מכוילת. ללא API אופציות חיצוני.</div>', unsafe_allow_html=True)
with st.sidebar:
    st.header("הגדרות")
    symbol=st.text_input("סימול", value="SPY").upper().strip()
    period=st.selectbox("תקופה לנתונים", ["5d","1mo","3mo","6mo"], index=1)
    interval=st.selectbox("טיים פריים", ["5m","15m","30m","1h","1d"], index=1)
    horizon=st.selectbox("אופק בדיקה", [3,5,8,13,21], index=2, help="כמה נרות קדימה לבדוק הצלחה")
    account_size=st.number_input("גודל חשבון ($)", min_value=100.0, value=10000.0, step=100.0)
    risk_pct=st.slider("סיכון לעסקה (%)", 0.25, 5.0, 1.0, 0.25)
    run=st.button("נתח עכשיו", type="primary", use_container_width=True)
if run and symbol:
    with st.spinner("מושך נתונים, מחשב אינדיקטורים ומריץ בדיקת עבר..."):
        df,err=get_stock_history(symbol,period=period,interval=interval)
        if err: st.error(err); st.stop()
        if df.empty: st.warning("לא התקבלו נתונים."); st.stop()
        df=add_indicators(df)
        if len(df)<80: st.warning("אין מספיק נתונים ל־Backtest איכותי. נסה תקופה ארוכה יותר."); st.stop()
        levels=detect_levels(df); patterns=detect_patterns(df); news_items=get_news(symbol)
        result=analyze_symbol(symbol,df,levels,patterns,horizon=horizon,account_size=account_size,risk_pct=risk_pct)
    color="#16a34a" if result["action"]=="CALL" else "#dc2626" if result["action"]=="PUT" else "#f59e0b"
    icon="🟢" if result["action"]=="CALL" else "🔴" if result["action"]=="PUT" else "🟡"
    c1,c2,c3=st.columns([1.15,1,1])
    with c1: st.markdown(f'<div class="signal-box" style="background:{color};">{icon}<br>{result["action"]}<br>{result["bias"]}</div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="score-box"><div>הסתברות Up</div><div class="score-number">{result["prob_up"]}%</div><div>אמינות: {result["confidence"]}%</div></div>', unsafe_allow_html=True)
    with c3: st.metric("מחיר אחרון", f'{result["last_close"]:.2f}'); st.metric("ציון מנוע", f'{result["score"]}/100')
    st.progress(result["prob_up"]/100, text=f'הסתברות לעלייה באופק {horizon} נרות: {result["prob_up"]}%')
    st.info(result["summary"])
    if result["confidence"]<60: st.markdown('<div class="warn">אמינות בינונית/נמוכה: המדגם קטן או שהאינדיקטורים לא מסכימים. עדיף להמתין לאישור.</div>', unsafe_allow_html=True)
    st.subheader("תוכנית טרייד"); st.table(pd.DataFrame([result["trade_plan"]]))
    pdf_bytes=create_pdf_report(symbol,result,levels,patterns)
    st.download_button("הורד דוח PDF", data=pdf_bytes, file_name=f"{symbol}_v7_quant_report.pdf", mime="application/pdf", use_container_width=True)
    tab7,tab6,tab5,tab4,tab3,tab2,tab1=st.tabs(["חדשות","Backtest","ניהול סיכון","רמות ותבניות","פירוק ניקוד","אינדיקטורים","גרף מקצועי"])
    with tab1:
        fig=make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=0.04,row_heights=[0.62,0.20,0.18])
        fig.add_trace(go.Candlestick(x=df.index,open=df["Open"],high=df["High"],low=df["Low"],close=df["Close"],name="מחיר"),row=1,col=1)
        for col,name,width in [("VWAP","VWAP",2),("EMA20","EMA20",1),("EMA50","EMA50",1),("EMA200","EMA200",2),("BB_Upper","BB עליון",1),("BB_Lower","BB תחתון",1)]:
            if col in df: fig.add_trace(go.Scatter(x=df.index,y=df[col],name=name,line=dict(width=width)),row=1,col=1)
        fig.add_hline(y=levels["support"],line_dash="dash",annotation_text="תמיכה",row=1,col=1)
        fig.add_hline(y=levels["resistance"],line_dash="dash",annotation_text="התנגדות",row=1,col=1)
        fig.add_trace(go.Bar(x=df.index,y=df["Volume"],name="Volume"),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["RSI"],name="RSI"),row=3,col=1)
        fig.add_hline(y=70,line_dash="dot",row=3,col=1); fig.add_hline(y=30,line_dash="dot",row=3,col=1)
        fig.update_layout(height=850,xaxis_rangeslider_visible=False,margin=dict(l=20,r=20,t=40,b=20),legend=dict(orientation="h"),title=f"{symbol} | {period} | {interval}")
        st.plotly_chart(fig,use_container_width=True)
    with tab2: st.dataframe(pd.DataFrame([result["latest_indicators"]]), use_container_width=True)
    with tab3: st.table(pd.DataFrame(result["checks"]))
    with tab4:
        st.subheader("רמות מפתח"); st.table(pd.DataFrame([levels]))
        st.subheader("תבניות נרות"); st.table(pd.DataFrame(patterns))
    with tab5: st.table(pd.DataFrame([result["risk_plan"]]))
    with tab6:
        st.subheader("תוצאות בדיקת עבר"); st.table(pd.DataFrame([result["backtest_summary"]]))
        hist=result.get("backtest_trades",[])
        if hist: st.dataframe(pd.DataFrame(hist).tail(50), use_container_width=True)
        else: st.warning("לא נמצאו מספיק עסקאות דומות במדגם.")
    with tab7:
        if news_items:
            for n in news_items[:8]: st.markdown(f'**{n.get("title","")}**'); st.caption(n.get("publisher","")); st.write(n.get("link","")); st.divider()
        else: st.info("לא נמצאו חדשות.")
else:
    st.markdown('<div class="note">הכנס סימול ולחץ נתח עכשיו. המערכת תחשב מגמה, הסתברות, Backtest פנימי, תבניות נרות ותוכנית סיכון.</div>', unsafe_allow_html=True)
