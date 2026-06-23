from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_pdf_report(symbol, report, levels, options, patterns):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(width - 40, y, f"Options Daily Trend AI Pro - {symbol}")
    y -= 35
    c.setFont("Helvetica", 12)
    lines = [
        f"Action: {report['action']}",
        f"Trend: {report['trend']}",
        f"Score: {report['score']}/100",
        f"Confidence: {report['confidence']}%",
        f"Last price: {report['last_close']:.2f}",
        f"Support: {levels['support']} | Resistance: {levels['resistance']}",
        f"Max Pain: {options.get('max_pain')}",
        f"Call Wall: {options.get('call_wall')} | Put Wall: {options.get('put_wall')}",
        "",
        "Trade Plan:",
    ]
    for k, v in report["trade_plan"].items():
        lines.append(f"{k}: {v}")
    lines += ["", "Summary:", report["summary"], "", "Educational only. Not investment advice."]
    for line in lines:
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 12)
        c.drawRightString(width - 40, y, str(line)[:105])
        y -= 18
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
