from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_pdf_report(symbol, result, levels, patterns):
    b = BytesIO(); c = canvas.Canvas(b, pagesize=A4); w,h = A4; y = h-50
    c.setFont("Helvetica-Bold", 18); c.drawRightString(w-40, y, f"Options Daily Trend AI v8 - {symbol}"); y -= 35
    c.setFont("Helvetica", 12)
    lines = [f"Action: {result['action']}", f"Grade: {result['grade']}", f"CALL: {result['call_prob']}% | PUT: {result['put_prob']}% | WAIT: {result['wait_prob']}%", f"Confidence: {result['confidence']}%", f"Last Close: {result['last_close']:.2f}", f"Support: {levels['support']} | Resistance: {levels['resistance']}", "", "Trade Plan:"]
    for k,v in result["trade_plan"].items(): lines.append(f"{k}: {v}")
    lines += ["", "Risk Plan:"]
    for k,v in result["risk_plan"].items(): lines.append(f"{k}: {v}")
    lines += ["", "Summary:", result["summary"], "", "Educational only. Not investment advice."]
    for line in lines:
        if y < 50:
            c.showPage(); y = h-50; c.setFont("Helvetica", 12)
        c.drawRightString(w-40, y, str(line)[:105]); y -= 18
    c.save(); b.seek(0); return b.getvalue()
