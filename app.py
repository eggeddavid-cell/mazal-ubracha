import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data import get_market_data, get_news
from indicators import add_indicators, detect_levels, detect_patterns
from engine import analyze_symbol, scan_symbols
from pdf_report import create_pdf_report

st.set_page_config(page_title='Options Daily Trend AI v10 Scanner', layout='wide')
st.markdown('''
<style>
html, body, [class*="css"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
h1,h2,h3,h4,h5,h6,p,label { text-align:right; }
div[data-testid="stMetric"] { text-align:center;background:#f8fafc;padding:14px;border-radius:14px;border:1px solid #e5e7eb; }
.big-title { font-size:38px;font-weight:950;margin-bottom:4px; }
.small-muted { color:#64748b;font-size:14px; }
.signal-box { padding:24px;border-radius:20px;color:white;font-size:32px;font-weight:950;text-align:center; }
.score-box { padding:24px;border-radius:20px;background:#0f172a;color:white;text-align:center; }
.score-number { font-size:52px;font-weight:950; }
.note { background:#eef6ff;border:1px solid #bfdbfe;padding:14px;border-radius:12px; }
.warn { background:#fff7ed;border:1px solid #fed7aa;padding:14px;border-radius:12px; }
</style>
''', unsafe_allow_html=True)

st.markdown('<div class="big-title">Options Daily Trend AI v10 Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="small-muted">Smart Flow Engine | Setup Scanner | Alpha Vantage + Yahoo fallback | ללא Python מקומי</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header('הגדרות')
    mode = st.radio('מצב עבודה', ['ניתוח סימול', 'סורק טריידים'], index=0)
    symbol = st.text_input('סימול', value='SPY').upper().strip()
    watchlist_text = st.text_area('רשימת סריקה', value='SPY,QQQ,AAPL,NVDA,TSLA,MSFT,META,AMZN,AMD,GOOGL')
    primary_interval = st.selectbox('טיים פריים ראשי', ['5min','15min','30min','60min','daily'], index=1)
    horizon = st.selectbox('אופק בדיקה בנרות', [3,5,8,13,21], index=2)
    account_size = st.number_input('גודל חשבון ($)', min_value=100.0, value=10000.0, step=100.0)
    risk_pct = st.slider('סיכון לעסקה (%)', 0.25, 5.0, 1.0, 0.25)
    run = st.button('נתח עכשיו', type='primary', use_container_width=True)

if run and mode == 'סורק טריידים':
    symbols = [x.strip().upper() for x in watchlist_text.split(',') if x.strip()]
    with st.spinner('סורק סימולים ומדרג Setup...'):
        scan_df = scan_symbols(symbols, interval=primary_interval, horizon=horizon)
    st.subheader('Setup Scanner')
    if scan_df.empty:
        st.warning('לא התקבלו תוצאות סריקה.')
    else:
        st.dataframe(scan_df, use_container_width=True)
        best = scan_df.iloc[0].to_dict()
        st.success(f"הטרייד החזק כרגע: {best.get('סימול')} | {best.get('פעולה')} | Grade {best.get('Grade')} | ציון {best.get('ציון איכות')}")
        st.caption('הסורק מדרג לפי מגמה, מומנטום, נפח, תנודתיות, Backtest ויחס סיכון/סיכוי. לא ייעוץ השקעות.')

elif run and symbol:
    with st.spinner('מושך נתונים ומחשב Smart Flow...'):
        main_df, main_source, main_err = get_market_data(symbol, interval=primary_interval)
        if main_err:
            st.error(main_err); st.stop()
        if main_df.empty:
            st.warning('לא התקבלו נתוני מחיר.'); st.stop()
        main_df = add_indicators(main_df)
        if len(main_df) < 80:
            st.warning('אין מספיק נתונים לניתוח איכותי. נסה טיים־פריים אחר.'); st.stop()
        tf_data = {}
        for nm, iv in [('15m','15min'), ('1h','60min'), ('Daily','daily')]:
            d, _, _ = get_market_data(symbol, interval=iv)
            if d is not None and not d.empty:
                try: tf_data[nm] = add_indicators(d)
                except Exception: pass
        levels = detect_levels(main_df); patterns = detect_patterns(main_df); news_items = get_news(symbol)
        result = analyze_symbol(symbol, main_df, levels, patterns, tf_data, horizon, account_size, risk_pct)

    color = '#16a34a' if 'CALL' in result['action'] else '#dc2626' if 'PUT' in result['action'] else '#f59e0b'
    icon = '🟢' if 'CALL' in result['action'] else '🔴' if 'PUT' in result['action'] else '🟡'
    c1,c2,c3 = st.columns([1.15,1,1])
    with c1: st.markdown(f'<div class="signal-box" style="background:{color};">{icon}<br>{result["action"]}<br>Grade {result["grade"]}</div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="score-box"><div>ציון איכות</div><div class="score-number">{result["quality_score"]}</div><div>אמינות: {result["confidence"]}%</div></div>', unsafe_allow_html=True)
    with c3:
        st.metric('מחיר אחרון', f'{result["last_close"]:.2f}')
        st.metric('Risk', result['risk_label'])
    st.progress(result['quality_score']/100, text=f'ציון איכות Setup: {result["quality_score"]}/100')
    st.info(result['summary'])
    if result['grade'] in ['C','D']:
        st.markdown('<div class="warn">Setup חלש או לא חד־משמעי. עדיף להמתין לאישור נוסף.</div>', unsafe_allow_html=True)
    st.subheader('תוכנית טרייד')
    st.table(pd.DataFrame([result['trade_plan']]))
    pdf_bytes = create_pdf_report(symbol, result, levels, patterns)
    st.download_button('הורד דוח PDF', data=pdf_bytes, file_name=f'{symbol}_v10_scanner_report.pdf', mime='application/pdf', use_container_width=True)
    tabs = st.tabs(['חדשות','Backtest','ניהול סיכון','Flow Analysis','Multi-Timeframe','רמות ותבניות','פירוק ניקוד','אינדיקטורים','גרף מקצועי'])
    tab_news, tab_bt, tab_risk, tab_flow, tab_mtf, tab_patterns, tab_checks, tab_ind, tab_chart = tabs
    with tab_chart:
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.62,0.20,0.18])
        fig.add_trace(go.Candlestick(x=main_df.index, open=main_df['Open'], high=main_df['High'], low=main_df['Low'], close=main_df['Close'], name='מחיר'), row=1, col=1)
        for col,name,width in [('VWAP','VWAP',2),('EMA20','EMA20',1),('EMA50','EMA50',1),('EMA200','EMA200',2),('BB_Upper','BB עליון',1),('BB_Lower','BB תחתון',1)]:
            fig.add_trace(go.Scatter(x=main_df.index, y=main_df[col], name=name, line=dict(width=width)), row=1, col=1)
        fig.add_hline(y=levels['support'], line_dash='dash', annotation_text='תמיכה', row=1, col=1)
        fig.add_hline(y=levels['resistance'], line_dash='dash', annotation_text='התנגדות', row=1, col=1)
        fig.add_trace(go.Bar(x=main_df.index, y=main_df['Volume'], name='Volume'), row=2, col=1)
        fig.add_trace(go.Scatter(x=main_df.index, y=main_df['RSI'], name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash='dot', row=3, col=1); fig.add_hline(y=30, line_dash='dot', row=3, col=1)
        fig.update_layout(height=850, xaxis_rangeslider_visible=False, legend=dict(orientation='h'), title=f'{symbol} | מקור: {main_source} | {primary_interval}')
        st.plotly_chart(fig, use_container_width=True)
    with tab_ind: st.dataframe(pd.DataFrame([result['latest_indicators']]), use_container_width=True)
    with tab_checks: st.table(pd.DataFrame(result['score_breakdown']))
    with tab_patterns:
        st.subheader('רמות מפתח'); st.table(pd.DataFrame([levels])); st.subheader('תבניות נרות'); st.table(pd.DataFrame(patterns))
    with tab_mtf: st.table(pd.DataFrame(result['multi_timeframe']))
    with tab_flow: st.table(pd.DataFrame([result['flow_analysis']]))
    with tab_risk: st.table(pd.DataFrame([result['risk_plan']]))
    with tab_bt:
        st.table(pd.DataFrame([result['backtest_summary']]))
        if result.get('backtest_trades'): st.dataframe(pd.DataFrame(result['backtest_trades']).tail(50), use_container_width=True)
    with tab_news:
        if news_items:
            for n in news_items[:8]:
                st.markdown(f'**{n.get("title","")}**'); st.caption(n.get('publisher','')); st.write(n.get('link','')); st.divider()
        else: st.info('לא נמצאו חדשות.')
else:
    st.markdown('<div class="note">בחר מצב עבודה: ניתוח סימול או סורק טריידים. אין צורך ב־Python מקומי.</div>', unsafe_allow_html=True)
