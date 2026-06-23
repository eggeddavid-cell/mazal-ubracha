from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_pdf_report(symbol, decision, levels, patterns, opt):
    b = BytesIO(); c = canvas.Canvas(b, pagesize=A4); w, h = A4; y = h - 45
    c.setFont("Helvetica-Bold", 18); c.drawRightString(w - 40, y, f"Options Pro Trade Engine - {symbol}"); y -= 30
    c.setFont("Helvetica", 11)
    lines = [f'Action: {decision["action"]}', f'Score: {decision["score"]}/100', f'Confidence: {decision["confidence"]}%', f'Last: {decision["last_price"]:.2f}', f'Support: {levels["support"]}', f'Resistance: {levels["resistance"]}', "", decision["summary"], "", "Trade Plan:"]
    for k, v in decision["trade_plan"].items(): lines.append(f"{k}: {v}")
    lines += ["", "Risk Management:"]
    for k, v in decision["risk_management"].items(): lines.append(f"{k}: {v}")
    if opt.get("available"):
        lines += ["", "Options:", f'PCR Vol: {opt.get("put_call_volume_ratio")}', f'Max Pain: {opt.get("max_pain")}', f'Bias: {opt.get("bias")}']
    for line in lines:
        if y < 45:
            c.showPage(); y = h - 45; c.setFont("Helvetica", 11)
        c.drawRightString(w - 40, y, str(line)[:100]); y -= 16
    c.setFont("Helvetica-Oblique", 9); c.drawRightString(w - 40, 25, "Educational only. Not investment advice."); c.save(); b.seek(0); return b.getvalue()
