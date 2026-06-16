import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data import get_stock_history, get_option_chain
from indicators import add_indicators, detect_levels
from news import get_news
from report import build_report
from pdf_report import create_pdf_report

st.set_page_config(page_title="Options Daily Trend AI", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
}
[data-testid="stSidebar"] {
    direction: rtl;
    text-align: right;
}
h1, h2, h3, h4, h5, h6, p, label {
    text-align: right;
}
div[data-testid="stMetric"] {
    text-align: center;
    background: #f8fafc;
    padding: 14px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
}
.big-title {
    font-size: 36px;
    font-weight: 900;
    margin-bottom: 4px;
}
.small-muted {
    color:#64748b;
    font-size:14px;
}
.trend-box {
    padding: 22px;
    border-radius: 18px;
    color: white;
    font-size: 30px;
    font-weight: 900;
    text-align: center;
}
.score-box {
    padding: 22px;
    border-radius: 18px;
    background: #0f172a;
    color: white;
    text-align: center;
}
.score-number {
    font-size: 48px;
    font-weight: 900;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">Options Daily Trend AI v3</div>', unsafe_allow_html=True)
st.markdown('<div class="small-muted">ממשק עברי מלא מימין לשמאל | נרות | אופציות | סיכוי/סיכון | דוח PDF</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("הגדרות")
    symbol = st.text_input("סימול", value="AAPL").upper().strip()
    period = st.selectbox("תקופה", ["1d", "5d", "1mo", "3mo", "6mo"], index=2)
    interval = st.selectbox("טיים פריים", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)
    run = st.button("נתח עכשיו", type="primary", use_container_width=True)

if run and symbol:
    with st.spinner("מושך נתונים ומחשב..."):
        df = get_stock_history(symbol, period=period, interval=interval)
        if df.empty:
            st.error("לא נמצאו נתונים. נסה סימול אחר או טיים פריים אחר.")
            st.stop()

        df = add_indicators(df)
        levels = detect_levels(df)
        options = get_option_chain(symbol)
        news_items = get_news(symbol)
        report = build_report(symbol, df, levels, options, news_items)

    trend_color = "#16a34a" if report["trend"] == "שורית" else "#dc2626" if report["trend"] == "דובית" else "#f59e0b"
    trend_icon = "🟢" if report["trend"] == "שורית" else "🔴" if report["trend"] == "דובית" else "🟡"

    top1, top2, top3 = st.columns([1.2, 1, 1])
    with top1:
        st.markdown(
            f'<div class="trend-box" style="background:{trend_color};">{trend_icon}<br>מגמה {report["trend"]}</div>',
            unsafe_allow_html=True
        )
    with top2:
        st.markdown(
            f'<div class="score-box"><div>ציון הסתברות</div><div class="score-number">{report["score"]}%</div></div>',
            unsafe_allow_html=True
        )
    with top3:
        st.metric("מחיר אחרון", f'{report["last_close"]:.2f}')
        st.metric("רמת סיכון", report["risk"])

    st.progress(report["score"] / 100, text=f'מד עוצמה/פחד-חמדנות: {report["score"]}/100')

    st.info(report["summary"])

    st.subheader("טבלת פעולה")
    st.table(pd.DataFrame([report["trade_plan"]]))

    pdf_bytes = create_pdf_report(symbol, report, levels, options)
    st.download_button(
        label="הפק דוח PDF בעברית",
        data=pdf_bytes,
        file_name=f"{symbol}_daily_report.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    tab4, tab3, tab2, tab1 = st.tabs(["חדשות", "אופציות", "בדיקות", "גרף מקצועי"])

    with tab1:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.72, 0.28]
        )

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name="מחיר"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="Bollinger עליון", line=dict(width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Middle"], name="Bollinger אמצע", line=dict(width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="Bollinger תחתון", line=dict(width=1)), row=1, col=1)

        fig.add_hline(y=levels["support"], line_dash="dash", annotation_text="תמיכה", row=1, col=1)
        fig.add_hline(y=levels["resistance"], line_dash="dash", annotation_text="התנגדות", row=1, col=1)

        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)

        fig.update_layout(
            height=760,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h"),
            title=f"{symbol} | {period} | {interval}"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("רמות מפתח")
        st.table(pd.DataFrame([levels]))

    with tab2:
        st.table(pd.DataFrame(report["checks"]))

    with tab3:
        if options:
            o1, o2, o3 = st.columns(3)
            o1.metric("Call Volume", f'{options.get("call_volume", 0):,}')
            o2.metric("Put Volume", f'{options.get("put_volume", 0):,}')
            o3.metric("Put/Call Volume", options.get("put_call_volume_ratio"))
            st.json(options)
        else:
            st.warning("נתוני אופציות לא זמינים במקור החינמי.")

    with tab4:
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
