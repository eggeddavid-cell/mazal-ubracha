from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_pdf_report(symbol, report, levels, options, patterns):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(width - 40, y, f"Options Daily Trend AI - {symbol}")
    y -= 35
    c.setFont("Helvetica", 12)
    lines = [
        f"Trend: {report['trend']}",
        f"Action: {report['action']}",
        f"Score: {report['score']}/100",
        f"Last price: {report['last_close']:.2f}",
        f"Support: {levels['support']}",
        f"Resistance: {levels['resistance']}",
        "",
        "Trade plan:",
    ]
    for k, v in report["trade_plan"].items():
        lines.append(f"{k}: {v}")
    if options:
        lines += ["", "Options:", f"Call Volume: {options.get('call_volume')}", f"Put Volume: {options.get('put_volume')}", f"Put/Call Ratio: {options.get('put_call_volume_ratio')}"]
    lines += ["", "Patterns:"]
    for p in patterns:
        lines.append(f"{p.get('תבנית')}: {p.get('משמעות')}")
    lines += ["", "Summary:", report["summary"]]
    for line in lines:
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 12)
        c.drawRightString(width - 40, y, str(line)[:95])
        y -= 18
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(width - 40, 30, "Educational use only. Not investment advice.")
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
