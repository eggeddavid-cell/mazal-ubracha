from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_pdf_report(symbol, result, levels, patterns, options=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    def draw(line, font="Helvetica", size=12):
        nonlocal y
        if y < 50:
            c.showPage()
            y = height - 50
        c.setFont(font, size)
        safe_line = str(line).replace("\n", " ")[:110]
        c.drawRightString(width - 40, y, safe_line)
        y -= 18

    draw(f"Options Daily Trend AI v10 - {symbol}", "Helvetica-Bold", 18)
    y -= 10

    draw(f"Action: {result.get('action', '')}")
    draw(f"Grade: {result.get('grade', '')}")
    draw(f"Quality Score: {result.get('quality_score', '')}/100")
    draw(f"Confidence: {result.get('confidence', '')}%")
    draw(f"Risk: {result.get('risk_label', '')}")
    draw(f"Last Close: {result.get('last_close', '')}")
    draw(f"CALL: {result.get('call_prob', '')}% | PUT: {result.get('put_prob', '')}% | WAIT: {result.get('wait_prob', '')}%")
    draw(f"Support: {levels.get('support', '')} | Resistance: {levels.get('resistance', '')}")

    draw("")
    draw("Trade Plan:", "Helvetica-Bold", 13)
    for k, v in result.get("trade_plan", {}).items():
        draw(f"{k}: {v}")

    draw("")
    draw("Risk Plan:", "Helvetica-Bold", 13)
    for k, v in result.get("risk_plan", {}).items():
        draw(f"{k}: {v}")

    draw("")
    draw("Flow Analysis:", "Helvetica-Bold", 13)
    for k, v in result.get("flow_analysis", {}).items():
        draw(f"{k}: {v}")

    draw("")
    draw("Patterns:", "Helvetica-Bold", 13)
    for p in patterns or []:
        if isinstance(p, dict):
            draw(f"{p.get('תבנית', '')} | {p.get('כיוון', '')} | {p.get('עוצמה', '')}")

    if options:
        draw("")
        draw("Options Data:", "Helvetica-Bold", 13)
        for k in ["max_pain", "call_wall", "put_wall", "put_call_oi_ratio", "gex_proxy"]:
            draw(f"{k}: {options.get(k, '')}")

    draw("")
    draw("Summary:", "Helvetica-Bold", 13)
    draw(result.get("summary", ""))

    draw("")
    draw("Educational only. Not investment advice.", "Helvetica-Oblique", 9)

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
