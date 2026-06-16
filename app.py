import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data import get_stock_history, get_option_chain
from indicators import add_indicators, detect_levels
from news import get_news
from report import build_report

st.set_page_config(page_title="Options Daily Trend AI", layout="wide")

st.markdown("""
<style>
.metric-card {padding:18px;border-radius:16px;background:#f7f9fc;border:1px solid #e5e7eb;}
.big-title {font-size:34px;font-weight:800;}
.small-muted {color:#64748b;font-size:14px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">Options Daily Trend AI</div>', unsafe_allow_html=True)
st.markdown('<div class="small-muted">ניתוח טכני + אופציות + חדשות. לא ייעוץ השקעות.</div>', unsafe_allow_html=True)

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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("מגמה", report["trend"])
    c2.metric("ציון", f'{report["score"]}/100')
    c3.metric("מחיר אחרון", f'{report["last_close"]:.2f}')
    c4.metric("סיכון", report["risk"])

    st.info(report["summary"])

    tab1, tab2, tab3, tab4 = st.tabs(["גרף מקצועי", "בדיקות", "אופציות", "חדשות"])

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
            name="Price"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper", line=dict(width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Middle"], name="BB Middle", line=dict(width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower", line=dict(width=1)), row=1, col=1)

        fig.add_hline(y=levels["support"], line_dash="dash", annotation_text="Support", row=1, col=1)
        fig.add_hline(y=levels["resistance"], line_dash="dash", annotation_text="Resistance", row=1, col=1)

        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"), row=2, col=1)

        fig.update_layout(
            height=720,
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
