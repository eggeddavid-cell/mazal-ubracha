import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data import get_stock_history, get_option_chain_full
from indicators import add_indicators, detect_levels, detect_patterns, compute_market_regime
from options_analytics import analyze_options_chain
from engine import build_pro_trade_decision
from pdf_report import create_pdf_report

st.set_page_config(page_title="Options Pro Trade Engine v5", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] {direction:rtl;text-align:right;}
[data-testid="stSidebar"] {direction:rtl;text-align:right;}
h1,h2,h3,h4,h5,h6,p,label {text-align:right;}
div[data-testid="stMetric"]{text-align:center;background:#f8fafc;padding:14px;border-radius:14px;border:1px solid #e5e7eb;}
.big-title{font-size:38px;font-weight:900;margin-bottom:2px;}
.sub{color:#64748b;font-size:14px;margin-bottom:20px;}
.card{padding:22px;border-radius:20px;color:white;text-align:center;font-weight:900;}
.card-dark{padding:22px;border-radius:20px;background:#0f172a;color:white;text-align:center;}
.score{font-size:54px;font-weight:900;}
.warn{background:#fff7ed;border:1px solid #fed7aa;padding:14px;border-radius:14px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">Options Pro Trade Engine v5</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">מנוע מקצועי לבחירת טרייד: מחיר + מומנטום + תנודתיות + אופציות + תבניות + ניהול סיכונים</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("הגדרות")
    symbol = st.text_input("סימול", value="NVDA").upper().strip()
    period = st.selectbox("תקופה", ["5d", "1mo", "3mo", "6mo", "1y"], index=1)
    interval = st.selectbox("טיים פריים", ["5m", "15m", "30m", "1h", "1d"], index=1)
    account = st.number_input("גודל חשבון משוער ($)", min_value=100.0, value=10000.0, step=100.0)
    risk_pct = st.slider("סיכון לעסקה (%)", 0.25, 3.0, 1.0, 0.25)
    st.caption("לדיוק גבוה באופציות עדיף בעתיד Polygon/Tradier. כרגע Yahoo חינמי ומוגבל.")
    run = st.button("נתח כמו מקצוען", type="primary", use_container_width=True)

if run and symbol:
    with st.spinner("מחשב מודל מקצועי..."):
        df, err = get_stock_history(symbol, period=period, interval=interval)
        if err:
            st.error(err); st.stop()
        if df.empty or len(df) < 60:
            st.warning("אין מספיק נתונים. נסה תקופה ארוכה יותר או טיים פריים אחר."); st.stop()
        df = add_indicators(df)
        levels = detect_levels(df)
        patterns = detect_patterns(df)
        regime = compute_market_regime(df)
        chain = get_option_chain_full(symbol)
        opt = analyze_options_chain(chain, float(df["Close"].iloc[-1]))
        decision = build_pro_trade_decision(symbol, df, levels, patterns, regime, opt, account, risk_pct)

    color = {"CALL":"#16a34a", "PUT":"#dc2626", "WAIT":"#f59e0b"}[decision["action"]]
    icon = {"CALL":"🟢", "PUT":"🔴", "WAIT":"🟡"}[decision["action"]]
    c1, c2, c3, c4 = st.columns([1.3,1,1,1])
    with c1:
        st.markdown(f'<div class="card" style="background:{color};font-size:30px">{icon}<br>{decision["action"]}<br>{decision["trend"]}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card-dark"><div>ציון טרייד</div><div class="score">{decision["score"]}</div></div>', unsafe_allow_html=True)
    with c3:
        st.metric("אמינות האות", f'{decision["confidence"]}%')
        st.metric("יחס סיכון/סיכוי", decision["trade_plan"]["יחס סיכון/סיכוי"])
    with c4:
        st.metric("מחיר אחרון", f'{decision["last_price"]:.2f}')
        st.metric("סיכון", decision["risk_level"])

    st.progress(decision["score"]/100, text=f'ציון מקצועי: {decision["score"]}/100')
    st.markdown(f'<div class="warn"><b>סיכום:</b> {decision["summary"]}</div>', unsafe_allow_html=True)

    st.subheader("תוכנית טרייד מקצועית")
    st.table(pd.DataFrame([decision["trade_plan"]]))
    st.subheader("למה זה הטרייד / למה לא")
    colA, colB = st.columns(2)
    with colA:
        st.success("גורמים תומכים")
        st.table(pd.DataFrame(decision["positive_factors"]))
    with colB:
        st.error("גורמי סיכון")
        st.table(pd.DataFrame(decision["risk_factors"]))

    pdf = create_pdf_report(symbol, decision, levels, patterns, opt)
    st.download_button("הורד דוח מקצועי PDF", pdf, file_name=f"{symbol}_pro_trade_report.pdf", mime="application/pdf", use_container_width=True)

    tabs = st.tabs(["גרף מקצועי", "אופציות ו-Max Pain", "תבניות נרות", "בדיקות ניקוד", "ניהול סיכונים"])
    with tabs[0]:
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.62,0.2,0.18])
        fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="מחיר"), row=1, col=1)
        for col, name in [("VWAP","VWAP"),("EMA20","EMA20"),("EMA50","EMA50"),("EMA200","EMA200"),("BB_Upper","BB עליון"),("BB_Lower","BB תחתון")]:
            if col in df:
                fig.add_trace(go.Scatter(x=df.index, y=df[col], name=name, line=dict(width=1)), row=1, col=1)
        fig.add_hline(y=levels["support"], line_dash="dash", annotation_text="תמיכה", row=1, col=1)
        fig.add_hline(y=levels["resistance"], line_dash="dash", annotation_text="התנגדות", row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI"), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", row=3, col=1)
        fig.update_layout(height=850, xaxis_rangeslider_visible=False, legend=dict(orientation="h"), margin=dict(l=20,r=20,t=40,b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame([levels]))
    with tabs[1]:
        if opt.get("available"):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Put/Call Volume", opt.get("put_call_volume_ratio"))
            m2.metric("Put/Call OI", opt.get("put_call_oi_ratio"))
            m3.metric("Max Pain", opt.get("max_pain"))
            m4.metric("Call/Put Bias", opt.get("bias"))
            st.subheader("קירות אופציות")
            st.table(pd.DataFrame(opt.get("walls", [])))
            if opt.get("heatmap"):
                st.subheader("Heatmap סטרייקים")
                st.dataframe(pd.DataFrame(opt["heatmap"]), use_container_width=True)
        else:
            st.warning("לא התקבלו נתוני אופציות אמינים כרגע.")
    with tabs[2]:
        st.table(pd.DataFrame(patterns))
    with tabs[3]:
        st.table(pd.DataFrame(decision["checks"]))
    with tabs[4]:
        st.table(pd.DataFrame([decision["risk_management"]]))
        st.caption("החישוב חינוכי בלבד. לא ייעוץ השקעות.")
else:
    st.write("הכנס סימול ולחץ נתח כמו מקצוען.")
