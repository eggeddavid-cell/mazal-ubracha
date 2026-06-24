import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data import get_market_data, get_news
from indicators import add_indicators, detect_levels, detect_patterns
from engine import analyze_symbol, scan_symbols
from pdf_report import create_pdf_report

st.set_page_config(
    page_title="מזל וברכה | Options AI v11",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Inter', sans-serif;
}

/* Hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Top bar ── */
.topbar {
    background: #0a1628;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0;
}
.topbar-brand { display: flex; align-items: center; gap: 12px; }
.topbar-icon {
    width: 38px; height: 38px; border-radius: 9px;
    background: #f0b429;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 600; color: #0a1628;
    line-height: 1;
}
.topbar-name { color: white; font-size: 17px; font-weight: 600; }
.topbar-sub  { color: #64748b; font-size: 11px; }
.live-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3);
    color: #10b981; padding: 4px 12px; border-radius: 20px; font-size: 11px;
}
.live-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #10b981;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ── Signal cards (top row) ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 0;
}
.metric-card {
    background: white;
    padding: 16px 20px;
}
.metric-label { font-size: 11px; color: #64748b; font-weight: 500; margin-bottom: 4px; }
.metric-val   { font-size: 24px; font-weight: 600; color: #0f172a; line-height: 1.1; }
.metric-val.green { color: #059669; }
.metric-val.red   { color: #dc2626; }
.metric-val.gold  { color: #d97706; }
.metric-sub { font-size: 11px; color: #94a3b8; margin-top: 3px; }

/* ── Action hero ── */
.hero-card {
    background: #0a1628;
    border-radius: 14px;
    overflow: hidden;
    margin: 16px 0 12px;
}
.hero-header {
    padding: 18px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.action-badge {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 22px; border-radius: 8px; font-size: 22px; font-weight: 600;
}
.action-call { background: rgba(5,150,105,0.2); border: 1.5px solid #059669; color: #34d399; }
.action-put  { background: rgba(220,38,38,0.2); border: 1.5px solid #dc2626; color: #f87171; }
.action-wait { background: rgba(245,158,11,0.2); border: 1.5px solid #d97706; color: #fbbf24; }
.grade-badge {
    background: rgba(240,180,41,0.15); border: 1px solid rgba(240,180,41,0.3);
    color: #fbbf24; padding: 5px 14px; border-radius: 20px; font-size: 13px; font-weight: 600;
}
.hero-body { background: white; padding: 16px 22px; }
.prog-row { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }
.prog-label { font-size: 12px; color: #64748b; min-width: 80px; }
.prog-track {
    flex: 1; height: 6px; border-radius: 3px; background: #f1f5f9; overflow: hidden;
}
.prog-fill { height: 100%; border-radius: 3px; transition: width 0.6s; }
.prog-num { font-size: 13px; font-weight: 600; color: #0f172a; min-width: 40px; text-align: left; }

/* ── Info strip ── */
.info-strip {
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 10px; padding: 12px 16px;
    color: #1e40af; font-size: 13px; line-height: 1.5;
    margin-bottom: 14px;
    direction: rtl; text-align: right;
}
.warn-strip {
    background: #fff7ed; border: 1px solid #fed7aa;
    border-radius: 10px; padding: 12px 16px;
    color: #9a3412; font-size: 13px; margin-bottom: 14px;
}

/* ── Plan grid ── */
.plan-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px;
}
.plan-item {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 12px 14px;
}
.plan-key { font-size: 11px; color: #64748b; font-weight: 500; margin-bottom: 4px; }
.plan-val { font-size: 16px; font-weight: 600; color: #0f172a; }
.plan-val.green { color: #059669; }
.plan-val.red   { color: #dc2626; }

/* ── News card ── */
.news-card {
    background: white; border: 1px solid #e2e8f0;
    border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
}
.news-title { font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 5px; }
.news-meta  { font-size: 12px; color: #64748b; }
.news-summary { font-size: 13px; color: #334155; margin-top: 6px; line-height: 1.5; }

/* ── MTF table ── */
.mtf-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.mtf-table th {
    background: #f8fafc; padding: 10px 12px;
    font-size: 11px; font-weight: 600; color: #64748b;
    border-bottom: 1px solid #e2e8f0; text-align: right;
}
.mtf-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; color: #0f172a; }
.badge-call { background:#d1fae5; color:#065f46; padding:3px 10px; border-radius:10px; font-size:11px; font-weight:600; }
.badge-put  { background:#fee2e2; color:#7f1d1d; padding:3px 10px; border-radius:10px; font-size:11px; font-weight:600; }
.badge-wait { background:#fef3c7; color:#78350f; padding:3px 10px; border-radius:10px; font-size:11px; font-weight:600; }
.badge-pos  { background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:8px; font-size:11px; }
.badge-neg  { background:#fee2e2; color:#7f1d1d; padding:2px 8px; border-radius:8px; font-size:11px; }
.badge-neu  { background:#f1f5f9; color:#475569; padding:2px 8px; border-radius:8px; font-size:11px; }

/* ── Score row ── */
.score-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; background: #f8fafc; border-radius: 8px; margin-bottom: 6px;
    font-size: 13px; color: #0f172a;
}
.score-val { font-weight: 600; }
.score-pos { color: #059669; }
.score-neg { color: #dc2626; }
.score-neu { color: #64748b; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    direction: rtl;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox select,
[data-testid="stSidebar"] .stTextArea textarea {
    background: #1e293b !important;
    border-color: #334155 !important;
    color: #f1f5f9 !important;
}
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 12px !important; }
[data-testid="stSidebar"] .stButton button {
    background: #f0b429 !important; color: #0a1628 !important;
    font-weight: 600 !important; border: none !important; border-radius: 8px !important;
    font-size: 14px !important;
}

/* ── Footer ── */
.footer-bar {
    background: #f8fafc; border-top: 1px solid #e2e8f0;
    padding: 10px 22px; font-size: 11px; color: #94a3b8;
    display: flex; align-items: center; justify-content: space-between;
    margin-top: 16px;
}

/* ── Tabs override ── */
.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #e2e8f0; background: white; }
.stTabs [data-baseweb="tab"] {
    font-size: 13px !important; font-weight: 500 !important;
    padding: 10px 16px !important; color: #64748b !important;
}
.stTabs [aria-selected="true"] { color: #2563eb !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }
</style>
""", unsafe_allow_html=True)

# ─── TOP BAR ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div class="topbar-brand">
    <div class="topbar-icon">מ</div>
    <div>
      <div class="topbar-name">מזל וברכה</div>
      <div class="topbar-sub">Options Daily Trend AI v11 · David Pro</div>
    </div>
  </div>
  <div class="live-badge"><div class="live-dot"></div> Live · Alpha Vantage · FMP · Yahoo</div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ הגדרות")
    mode = st.radio("מצב עבודה", ["ניתוח סימול", "סורק טריידים"], index=0)
    st.divider()
    symbol = st.text_input("סימול", value="TSLA").upper().strip()
    watchlist_text = st.text_area("רשימת סריקה (פסיק)", value="SPY,QQQ,AAPL,NVDA,TSLA,MSFT,META,AMZN,AMD,GOOGL", height=80)
    primary_interval = st.selectbox("טיים פריים ראשי", ["5min", "15min", "30min", "60min", "daily"], index=1)
    horizon = st.selectbox("אופק (נרות)", [3, 5, 8, 13, 21], index=2)
    st.divider()
    account_size = st.number_input("גודל חשבון ($)", min_value=100.0, value=10000.0, step=500.0)
    risk_pct = st.slider("סיכון לעסקה (%)", 0.25, 5.0, 1.0, 0.25)
    st.caption(f"סיכון: **${account_size * risk_pct / 100:,.0f}** לעסקה")
    st.divider()
    run = st.button("▶  נתח עכשיו", type="primary", use_container_width=True)

# ─── SCANNER MODE ─────────────────────────────────────────────────────────────
if run and mode == "סורק טריידים":
    symbols = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]
    with st.spinner("סורק סימולים..."):
        scan_df = scan_symbols(symbols, interval=primary_interval, horizon=horizon)
    if scan_df.empty:
        st.warning("לא התקבלו תוצאות.")
    else:
        best = scan_df.iloc[0].to_dict()
        color = "#059669" if "CALL" in str(best.get("פעולה","")) else "#dc2626" if "PUT" in str(best.get("פעולה","")) else "#d97706"
        st.markdown(f"""
        <div style="background:{color}15;border:1.5px solid {color};border-radius:12px;padding:14px 18px;margin-bottom:14px;direction:rtl">
          <div style="font-size:12px;color:{color};font-weight:600;">🏆 הטרייד החזק ביותר</div>
          <div style="font-size:20px;font-weight:700;color:#0f172a;margin-top:4px">
            {best.get('סימול')} · {best.get('פעולה')} · Grade {best.get('Grade')} · ציון {best.get('ציון איכות')}
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.dataframe(scan_df, use_container_width=True, hide_index=True)

# ─── ANALYSIS MODE ────────────────────────────────────────────────────────────
elif run and symbol:
    with st.spinner(f"מושך נתונים עבור {symbol}..."):
        main_df, main_source, main_err = get_market_data(symbol, interval=primary_interval)
        if main_err:
            st.error(main_err); st.stop()
        if main_df.empty:
            st.warning("לא התקבלו נתוני מחיר."); st.stop()
        main_df = add_indicators(main_df)
        if len(main_df) < 80:
            st.warning("אין מספיק נתונים. נסה טיים-פריים אחר."); st.stop()

        tf_data = {}
        for nm, iv in [("15m","15min"), ("1h","60min"), ("Daily","daily")]:
            d, _, _ = get_market_data(symbol, interval=iv)
            if d is not None and not d.empty:
                try: tf_data[nm] = add_indicators(d)
                except: pass

        levels   = detect_levels(main_df)
        patterns = detect_patterns(main_df)
        news_items = get_news(symbol)
        result = analyze_symbol(symbol, main_df, levels, patterns, tf_data, horizon, account_size, risk_pct)

    action = result["action"]
    grade  = result["grade"]
    qs     = result["quality_score"]
    conf   = result["confidence"]
    last_p = result["last_close"]

    # price change
    price_chg = ""
    if len(main_df) >= 2:
        prev = float(main_df["Close"].iloc[-2])
        chg = (last_p - prev) / prev * 100
        chg_color = "#059669" if chg >= 0 else "#dc2626"
        price_chg = f'<span style="color:{chg_color};font-size:13px"> {chg:+.2f}%</span>'

    # ── Metric row
    action_color = "#059669" if "CALL" in action else "#dc2626" if "PUT" in action else "#d97706"
    action_class = "green" if "CALL" in action else "red" if "PUT" in action else "gold"
    risk_color   = "#059669" if result["risk_label"]=="LOW" else "#d97706" if result["risk_label"]=="MEDIUM" else "#dc2626"

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-label">מחיר אחרון · {symbol}</div>
        <div class="metric-val">${last_p:,.2f}{price_chg}</div>
        <div class="metric-sub">{primary_interval} · {main_source}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">סיגנל</div>
        <div class="metric-val {action_class}">{action}</div>
        <div class="metric-sub">Grade {grade}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">ציון איכות</div>
        <div class="metric-val gold">{qs} / 100</div>
        <div class="metric-sub">אמינות {conf}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">סיכון לעסקה</div>
        <div class="metric-val" style="color:{risk_color}">{result['risk_label']}</div>
        <div class="metric-sub">${account_size * risk_pct / 100:,.0f} · R:R {result['trade_plan'].get('יחס סיכון/סיכוי', 0):.1f}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Main content area
    main_area = st.container()
    with main_area:
        col_left, col_right = st.columns([2, 1])

        with col_left:
            # Hero action card
            action_cls = "action-call" if "CALL" in action else "action-put" if "PUT" in action else "action-wait"
            arrow = "↑" if "CALL" in action else "↓" if "PUT" in action else "—"
            st.markdown(f"""
            <div class="hero-card">
              <div class="hero-header">
                <div style="display:flex;align-items:center;gap:12px">
                  <div class="action-badge {action_cls}">{arrow} {action}</div>
                  <div class="grade-badge">Grade {grade}</div>
                </div>
                <div style="text-align:left;font-size:11px;color:#475569">
                  <div>{symbol} · {primary_interval}</div>
                  <div>CALL {result['call_prob']}% · PUT {result['put_prob']}%</div>
                </div>
              </div>
              <div class="hero-body">
                <div class="prog-row">
                  <div class="prog-label">ציון איכות</div>
                  <div class="prog-track"><div class="prog-fill" style="width:{qs}%;background:#059669"></div></div>
                  <div class="prog-num">{qs}/100</div>
                </div>
                <div class="prog-row">
                  <div class="prog-label">אמינות</div>
                  <div class="prog-track"><div class="prog-fill" style="width:{conf}%;background:#3b82f6"></div></div>
                  <div class="prog-num">{conf}%</div>
                </div>
                <div class="prog-row">
                  <div class="prog-label">{'CALL' if 'CALL' in action else 'PUT'}</div>
                  <div class="prog-track"><div class="prog-fill" style="width:{max(result['call_prob'],result['put_prob'])}%;background:{action_color}"></div></div>
                  <div class="prog-num">{max(result['call_prob'],result['put_prob'])}%</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Summary
            st.markdown(f'<div class="info-strip">✅ {result["summary"]}</div>', unsafe_allow_html=True)
            if grade in ["C", "D"]:
                st.markdown('<div class="warn-strip">⚠️ Setup באיכות נמוכה. מומלץ להמתין לאישור נוסף לפני כניסה.</div>', unsafe_allow_html=True)

        with col_right:
            # Trade plan
            tp = result["trade_plan"]
            rp = result["risk_plan"]
            st.markdown(f"""
            <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:16px;margin-top:0">
              <div style="font-size:13px;font-weight:600;color:#0f172a;margin-bottom:12px">📋 תוכנית טרייד</div>
              <div class="plan-grid">
                <div class="plan-item"><div class="plan-key">כניסה</div><div class="plan-val">${tp['כניסה']:.2f}</div></div>
                <div class="plan-item"><div class="plan-key">יעד 1</div><div class="plan-val green">${tp['יעד 1']:.2f}</div></div>
                <div class="plan-item"><div class="plan-key">יעד 2</div><div class="plan-val green">${tp['יעד 2']:.2f}</div></div>
                <div class="plan-item"><div class="plan-key">סטופ</div><div class="plan-val red">${tp['סטופ']:.2f}</div></div>
                <div class="plan-item"><div class="plan-key">R:R</div><div class="plan-val">{tp['יחס סיכון/סיכוי']:.2f}</div></div>
                <div class="plan-item"><div class="plan-key">כמות</div><div class="plan-val">{rp['כמות יחידות']}</div></div>
              </div>
              <div style="font-size:11px;color:#64748b;border-top:1px solid #f1f5f9;padding-top:10px;margin-top:4px">
                סיכון: ${rp['סיכון $']:.0f} · ATR: {rp['ATR']:.3f} · Risk: <span style="font-weight:600;color:{'#059669' if rp['Risk']=='LOW' else '#d97706' if rp['Risk']=='MEDIUM' else '#dc2626'}">{rp['Risk']}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # PDF download
            pdf_bytes = create_pdf_report(symbol, result, levels, patterns)
            st.download_button(
                "⬇️ הורד דוח PDF",
                data=pdf_bytes,
                file_name=f"{symbol}_v11_report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab_chart, tab_mtf, tab_flow, tab_news, tab_bt, tab_risk, tab_ind, tab_checks = st.tabs([
        "📊 גרף", "🕐 Multi-TF", "🔄 Flow Analysis",
        "📰 חדשות", "🧪 Backtest", "⚖️ סיכון",
        "📐 אינדיקטורים", "🏆 ניקוד"
    ])

    with tab_chart:
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            vertical_spacing=0.03, row_heights=[0.60, 0.22, 0.18]
        )
        # Candlesticks
        fig.add_trace(go.Candlestick(
            x=main_df.index, open=main_df["Open"], high=main_df["High"],
            low=main_df["Low"], close=main_df["Close"], name="מחיר",
            increasing_line_color="#059669", decreasing_line_color="#dc2626"
        ), row=1, col=1)
        # Overlays
        overlay_cfg = [
            ("VWAP","VWAP","#f0b429",2),("EMA20","EMA20","#3b82f6",1.5),
            ("EMA50","EMA50","#8b5cf6",1.5),("EMA200","EMA200","#ef4444",1),
            ("BB_Upper","BB+","#94a3b8",1),("BB_Lower","BB-","#94a3b8",1),
        ]
        for col, name, color, width in overlay_cfg:
            if col in main_df.columns:
                fig.add_trace(go.Scatter(
                    x=main_df.index, y=main_df[col], name=name,
                    line=dict(color=color, width=width, dash="dot" if "BB" in name else "solid"),
                    opacity=0.85
                ), row=1, col=1)
        # Support / resistance
        fig.add_hline(y=levels["support"], line_dash="dash", line_color="#059669",
                      annotation_text=f"תמיכה {levels['support']:.2f}", row=1, col=1)
        fig.add_hline(y=levels["resistance"], line_dash="dash", line_color="#dc2626",
                      annotation_text=f"התנגדות {levels['resistance']:.2f}", row=1, col=1)
        # Volume
        vol_colors = ["#059669" if c >= o else "#dc2626"
                      for c, o in zip(main_df["Close"], main_df["Open"])]
        fig.add_trace(go.Bar(
            x=main_df.index, y=main_df["Volume"], name="Volume",
            marker_color=vol_colors, opacity=0.7
        ), row=2, col=1)
        # RSI
        fig.add_trace(go.Scatter(
            x=main_df.index, y=main_df["RSI"], name="RSI",
            line=dict(color="#6366f1", width=1.5)
        ), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#dc2626", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#059669", row=3, col=1)
        fig.add_hrect(y0=30, y1=70, fillcolor="#f1f5f9", opacity=0.3, row=3, col=1)

        fig.update_layout(
            height=780, template="plotly_white",
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1.01, x=0),
            title=dict(text=f"{symbol} · {primary_interval} · {main_source}", font=dict(size=13, color="#64748b")),
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="Inter, sans-serif", size=11),
        )
        fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9", gridwidth=0.5)
        fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", gridwidth=0.5)
        st.plotly_chart(fig, use_container_width=True)

    with tab_mtf:
        mtf_data = result["multi_timeframe"]
        if mtf_data:
            st.markdown('<table class="mtf-table"><thead><tr><th>טיים פריים</th><th>כיוון</th><th>ציון</th></tr></thead><tbody>', unsafe_allow_html=True)
            for row in mtf_data:
                d = row.get("כיוון", "")
                badge_cls = "badge-call" if d == "CALL" else "badge-put" if d == "PUT" else "badge-wait"
                st.markdown(f'<tr><td>{row.get("טיים פריים","")}</td><td><span class="{badge_cls}">{d}</span></td><td>{row.get("ציון","")}</td></tr>', unsafe_allow_html=True)
            st.markdown('</tbody></table>', unsafe_allow_html=True)
        else:
            st.info("אין נתוני Multi-TF")

    with tab_flow:
        fa = result["flow_analysis"]
        cols = st.columns(5)
        flow_keys = ["Trend","Momentum","Volume","Volatility","Price Action"]
        for i, k in enumerate(flow_keys):
            v = fa.get(k, 0)
            with cols[i]:
                st.metric(k, v)
        st.divider()
        st.table(pd.DataFrame([fa]))

    with tab_news:
        st.subheader(f"חדשות {symbol}")
        if news_items:
            for n in news_items[:10]:
                title   = n.get("title", "")
                pub     = n.get("publisher", "")
                date    = n.get("date", "")
                summary = n.get("summary", "")
                link    = n.get("link", "#")
                source  = n.get("source", "")
                sentiment = n.get("sentiment", "")
                s_class = "badge-pos" if sentiment == "Bullish" else "badge-neg" if sentiment == "Bearish" else "badge-neu"
                s_label = "חיובי" if sentiment == "Bullish" else "שלילי" if sentiment == "Bearish" else "ניטרלי"
                st.markdown(f"""
                <div class="news-card">
                  <div class="news-title">{title}</div>
                  <div class="news-meta">{pub} · {source} · {date} &nbsp; <span class="{s_class}">{s_label}</span></div>
                  <div class="news-summary">{summary[:300]}</div>
                  <div style="margin-top:8px"><a href="{link}" target="_blank" style="font-size:12px;color:#3b82f6">פתח כתבה ↗</a></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("לא נמצאו חדשות. בדוק שה-API keys מוגדרים ב-Secrets.")

    with tab_bt:
        bt = result["backtest_summary"]
        wr  = bt.get("אחוז הצלחה")
        exp = bt.get("תוחלת R")
        samp= bt.get("עסקאות במדגם", 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("עסקאות", samp)
        c2.metric("אחוז הצלחה", f"{wr}%" if wr else "—")
        c3.metric("תוחלת R", f"{exp}" if exp else "—")
        trades = result.get("backtest_trades")
        if trades:
            df_bt = pd.DataFrame(trades).tail(50)
            st.dataframe(df_bt, use_container_width=True, hide_index=True)

    with tab_risk:
        rp2 = result["risk_plan"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("סיכון $", f"${rp2['סיכון $']:.0f}")
        c2.metric("כמות יחידות", rp2["כמות יחידות"])
        c3.metric("סיכון/יחידה", f"${rp2['סיכון ליחידה']:.2f}")
        c4.metric("ATR", f"{rp2['ATR']:.3f}")
        st.table(pd.DataFrame([rp2]))

    with tab_ind:
        li = result["latest_indicators"]
        cols = st.columns(5)
        for i, (k, v) in enumerate(li.items()):
            cols[i % 5].metric(k, v)

    with tab_checks:
        st.markdown("#### פירוט ניקוד")
        for item in result["score_breakdown"]:
            v = item["ציון"]
            cls = "score-pos" if v > 0 else "score-neg" if v < 0 else "score-neu"
            st.markdown(f'<div class="score-row"><span>{item["רכיב"]}</span><span class="score-val {cls}">{v:+}</span></div>', unsafe_allow_html=True)

    # Footer
    st.markdown(f"""
    <div class="footer-bar">
      <span>מקורות: Yahoo Finance · Alpha Vantage · FMP · {main_source}</span>
      <span>לא ייעוץ השקעות. David Pro v11</span>
    </div>
    """, unsafe_allow_html=True)

else:
    # Welcome screen
    st.markdown("""
    <div style="max-width:680px;margin:60px auto;text-align:center;direction:rtl">
      <div style="font-size:52px;margin-bottom:16px">📈</div>
      <div style="font-size:28px;font-weight:700;color:#0f172a;margin-bottom:8px">מזל וברכה</div>
      <div style="font-size:15px;color:#64748b;margin-bottom:32px">Options Daily Trend AI v11 · Smart Flow Engine</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;text-align:center">
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px">
          <div style="font-size:22px">🎯</div>
          <div style="font-size:13px;font-weight:600;color:#0f172a;margin-top:6px">Smart Flow Engine</div>
          <div style="font-size:11px;color:#64748b;margin-top:4px">ניתוח טכני מולטי-דימנסיוני</div>
        </div>
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px">
          <div style="font-size:22px">🔍</div>
          <div style="font-size:13px;font-weight:600;color:#0f172a;margin-top:6px">Setup Scanner</div>
          <div style="font-size:11px;color:#64748b;margin-top:4px">סריקה אוטומטית של רשימת מעקב</div>
        </div>
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px">
          <div style="font-size:22px">📊</div>
          <div style="font-size:13px;font-weight:600;color:#0f172a;margin-top:6px">Multi-Timeframe</div>
          <div style="font-size:11px;color:#64748b;margin-top:4px">יישור 4 טיים פריימים</div>
        </div>
      </div>
      <div style="margin-top:28px;font-size:13px;color:#94a3b8">
        ← הכנס סימול ולחץ <strong>נתח עכשיו</strong> בסייד-בר
      </div>
    </div>
    """, unsafe_allow_html=True)
