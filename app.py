import streamlit as st
import pandas as pd
from data import get_stock_history, get_option_chain
from indicators import add_indicators, detect_levels, score_trend
from news import get_news
from report import build_report

st.set_page_config(page_title="Options Daily Trend AI", layout="wide")

st.title("Options Daily Trend AI")
st.caption("ניתוח יומי טכני + אופציות + חדשות. לא ייעוץ השקעות.")

symbol = st.text_input("הכנס סימול", value="AAPL").upper().strip()
period = st.selectbox("תקופה לניתוח", ["5d", "1mo", "3mo"], index=1)
interval = st.selectbox("טיים פריים", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)

run = st.button("נתח עכשיו", type="primary")

if run and symbol:
    with st.spinner("מושך נתונים ומחשב אינדיקטורים..."):
        df = get_stock_history(symbol, period=period, interval=interval)
        if df.empty:
            st.error("לא נמצאו נתונים לסימול הזה.")
            st.stop()

        df = add_indicators(df)
        levels = detect_levels(df)
        options = get_option_chain(symbol)
        news_items = get_news(symbol)
        report = build_report(symbol, df, levels, options, news_items)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("מגמה", report["trend"])
    col2.metric("ציון", f'{report["score"]}/100')
    col3.metric("מחיר אחרון", f'{report["last_close"]:.2f}')
    col4.metric("סיכון", report["risk"])

    st.subheader("סיכום מקצועי")
    st.write(report["summary"])

    st.subheader("רמות מפתח")
    st.table(pd.DataFrame([levels]))

    st.subheader("בדיקות")
    st.table(pd.DataFrame(report["checks"]))

    st.subheader("גרף")
    st.line_chart(df[["Close", "VWAP", "BB_Middle", "BB_Upper", "BB_Lower"]].dropna())

    st.subheader("אופציות")
    if options:
        st.json(options)
    else:
        st.info("נתוני אופציות לא זמינים במקור החינמי. לדיוק גבוה מומלץ לחבר Polygon / Tradier.")

    st.subheader("חדשות")
    if news_items:
        for n in news_items[:5]:
            st.write(f'**{n.get("title","")}**')
            st.caption(n.get("publisher",""))
            st.write(n.get("link",""))
    else:
        st.info("לא נמצאו חדשות.")
