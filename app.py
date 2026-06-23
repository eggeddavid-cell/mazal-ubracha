import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data import get_stock_history
from options_data import get_options_analysis
from indicators import add_indicators, detect_levels, detect_patterns
from news import get_news
from report import build_report
from pdf_report import create_pdf_report

st.set_page_config(page_title="Options Daily Trend AI", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
h1,h2,h3,h4,h5,h6,p,label { text-align: right; }
div[data-testid="stMetric"] { text-align:center;background:#f8fafc;padding:14px;border-radius:14px;border:1px solid #e5e7eb; }
.big-title { font-size:36px;font-weight:900;margin-bottom:4px; }
.small-muted { color:#64748b;font-size:14px; }
.trend-box { padding:22px;border-radius:18px;color:white;font-size:30px;font-weight:900;text-align:center; }
.score-box { padding:22px;border-radius:18px;background:#0f172a;color:white;text-align:center; }
.score-number { font-size:48px;font-weight:900; }
.warn { background:#fff7ed;border:1px solid #fed7aa;padding:14px;border-radius:12px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">Options Daily Trend AI v6 Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="small-muted">מקור אופציות מקצועי: Tradier / Polygon API + גיבוי Yahoo | Max Pain | Option Walls | GEX בסיסי | ניהול סיכון</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("הגדרות")
    symbol = st.text_input("סימול", value="SPY").upper().strip()
    period = st.selectbox("תקופה", ["1d", "5d", "1mo", "3mo", "6mo"], index=1)
    interval = st.selectbox("טיים פריים", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)
    account_size = st.number_input("גודל חשבון ($)", min_value=100.0, value=10000.0, step=100.0)
    risk_pct = st.slider("סיכון לעסקה (%)", 0.25, 5.0, 1.0, 0.25)
    st.caption("לנתוני אופציות מקצועיים: הוסף TRADIER_TOKEN או POLYGON_API_KEY ב־Streamlit Secrets.")
    run = st.button("נתח עכשיו", type="primary", use_container_width=True)

if run and symbol:
    with st.spinner("מושך נתונים ומחשב..."):
        df, data_error = get_stock_history(symbol, period=period, interval=interval)
        if data_error:
            st.error(data_error)
            st.stop()
        if df.empty:
            st.warning("לא התקבלו נתוני מחיר. נסה 5d / 15m או סימול אחר.")
            st.stop()

        df = add_indicators(df)
        if len(df) < 25:
            st.warning("אין מספיק נתונים לחישוב איכותי.")
            st.stop()

        levels = detect_levels(df)
        patterns = detect_patterns(df)
        options_analysis = get_options_analysis(symbol, float(df["Close"].iloc[-1]))
        news_items = get_news(symbol)
        report = build_report(symbol, df, levels, options_analysis, news_items, patterns, account_size, risk_pct)

    trend_color = "#16a34a" if report["trend"] == "שורית" else "#dc2626" if report["trend"] == "דובית" else "#f59e0b"
    trend_icon = "🟢" if report["trend"] == "שורית" else "🔴" if report["trend"] == "דובית" else "🟡"

    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        st.markdown(f'<div class="trend-box" style="background:{trend_color};">{trend_icon}<br>מגמה {report["trend"]}<br>{report["action"]}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="score-box"><div>ציון הסתברות</div><div class="score-number">{report["score"]}%</div><div>אמינות: {report["confidence"]}%</div></div>', unsafe_allow_html=True)
    with c3:
        st.metric("מחיר אחרון", f'{report["last_close"]:.2f}')
        st.metric("רמת סיכון", report["risk"])

    st.progress(report["score"] / 100, text=f'מד עוצמה: {report["score"]}/100')
    st.info(report["summary"])

    if options_analysis.get("source") in ["none", "yahoo_limited"]:
        st.markdown('<div class="warn">נתוני האופציות מוגבלים. כדי לקבל Max Pain / Walls / GEX אמינים, הוסף TRADIER_TOKEN או POLYGON_API_KEY ל־Streamlit Secrets.</div>', unsafe_allow_html=True)

    st.subheader("תוכנית טרייד מקצועית")
    st.table(pd.DataFrame([report["trade_plan"]]))

    pdf_bytes = create_pdf_report(symbol, report, levels, options_analysis, patterns)
    st.download_button("הורד דוח מקצועי PDF", data=pdf_bytes, file_name=f"{symbol}_pro_trade_report.pdf", mime="application/pdf", use_container_width=True)

    tab6, tab5, tab4, tab3, tab2, tab1 = st.tabs(["חדשות", "ניהול סיכונים", "אופציות Pro", "תבניות נרות", "בדיקות ניקוד", "גרף מקצועי"])

    with tab1:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.72, 0.28])
        fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="מחיר"), row=1, col=1)
        for col, name, width in [("EMA20","EMA20",1), ("EMA50","EMA50",1), ("EMA200","EMA200",2), ("VWAP","VWAP",2), ("BB_Upper","Bollinger עליון",1), ("BB_Lower","Bollinger תחתון",1)]:
            if col in df:
                fig.add_trace(go.Scatter(x=df.index, y=df[col], name=name, line=dict(width=width)), row=1, col=1)
        fig.add_hline(y=levels["support"], line_dash="dash", annotation_text="תמיכה", row=1, col=1)
        fig.add_hline(y=levels["resistance"], line_dash="dash", annotation_text="התנגדות", row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)
        fig.update_layout(height=760, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=40, b=20), legend=dict(orientation="h"), title=f"{symbol} | {period} | {interval}")
        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame([levels]))

    with tab2:
        st.table(pd.DataFrame(report["checks"]))

    with tab3:
        st.table(pd.DataFrame(patterns))

    with tab4:
        st.metric("מקור נתוני אופציות", options_analysis.get("source", "none"))
        st.metric("Max Pain", options_analysis.get("max_pain", "לא זמין"))
        w1, w2, w3 = st.columns(3)
        w1.metric("Call Wall", options_analysis.get("call_wall", "לא זמין"))
        w2.metric("Put Wall", options_analysis.get("put_wall", "לא זמין"))
        w3.metric("GEX Bias", options_analysis.get("gex_bias", "לא זמין"))

        heatmap = options_analysis.get("chain_table", [])
        if heatmap:
            st.subheader("Heatmap סטרייקים")
            st.dataframe(pd.DataFrame(heatmap), use_container_width=True)
        else:
            st.warning("לא התקבלו נתוני אופציות מלאים.")

    with tab5:
        st.table(pd.DataFrame([report["risk_plan"]]))

    with tab6:
        if news_items:
            for n in news_items[:8]:
                st.markdown(f'**{n.get("title","")}**')
                st.caption(n.get("publisher",""))
                st.write(n.get("link",""))
                st.divider()
        else:
            st.info("לא נמצאו חדשות.")
else:
    st.write("הכנס סימול ולחץ נתח עכשיו.")
