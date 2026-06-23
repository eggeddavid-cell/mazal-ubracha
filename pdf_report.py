from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_pdf_report(symbol, result, levels, patterns):
    buffer=BytesIO(); c=canvas.Canvas(buffer,pagesize=A4); width,height=A4; y=height-50
    c.setFont("Helvetica-Bold",18); c.drawRightString(width-40,y,f"Options Daily Trend AI v7 Quant - {symbol}"); y-=35
    c.setFont("Helvetica",12)
    lines=[f"Action: {result['action']}",f"Bias: {result['bias']}",f"Score: {result['score']}/100",f"Probability Up: {result['prob_up']}%",f"Confidence: {result['confidence']}%",f"Last Close: {result['last_close']:.2f}",f"Support: {levels['support']} | Resistance: {levels['resistance']}","","Trade Plan:"]
    for k,v in result["trade_plan"].items(): lines.append(f"{k}: {v}")
    lines += ["","Risk Plan:"]
    for k,v in result["risk_plan"].items(): lines.append(f"{k}: {v}")
    lines += ["","Backtest:"]
    for k,v in result["backtest_summary"].items():
        if k not in ["sample","win_rate","call_win","put_win","expectancy"]: lines.append(f"{k}: {v}")
    lines += ["","Summary:",result["summary"],"","Educational only. Not investment advice."]
    for line in lines:
        if y<50: c.showPage(); y=height-50; c.setFont("Helvetica",12)
        c.drawRightString(width-40,y,str(line)[:105]); y-=18
    c.save(); buffer.seek(0); return buffer.getvalue()
