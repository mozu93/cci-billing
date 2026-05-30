# app/services/pdf/receipt_pdf.py
import os
from datetime import date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen.canvas import Canvas
from app.services.pdf.fonts import register_fonts, FONT_NORMAL, FONT_BOLD

C_BOX    = HexColor("#E2E8F0")
C_BORDER = HexColor("#475569")
C_BLUE   = HexColor("#1E40AF")
C_GRAY   = HexColor("#64748B")


def _draw_receipt(c: Canvas, issuance, company, x: float, y: float,
                  w: float, h: float) -> None:
    pad = 3 * mm

    c.setStrokeColor(C_BORDER)
    c.setLineWidth(1)
    c.rect(x, y, w, h)

    c.setFillColor(C_BLUE)
    c.setFont(FONT_BOLD, 16)
    c.drawCentredString(x + w / 2, y + h - 10*mm, "領　収　書")

    issue_date = getattr(issuance, 'issued_at', None)
    date_str = (issue_date.strftime("%Y年%m月%d日") if issue_date
                else date.today().strftime("%Y年%m月%d日"))
    c.setFillColor(C_GRAY)
    c.setFont(FONT_NORMAL, 7)
    c.drawString(x + pad, y + h - 14*mm, f"No. {issuance.doc_number}")
    c.drawRightString(x + w - pad, y + h - 14*mm, f"発行日：{date_str}")

    c.setStrokeColor(C_BLUE)
    c.setLineWidth(1.5)
    c.line(x + pad, y + h - 16*mm, x + w - pad, y + h - 16*mm)

    recipient = (issuance.recipient_organization or issuance.recipient_name or "").strip()
    c.setFillColor(black)
    c.setFont(FONT_BOLD, 12)
    c.drawString(x + pad, y + h - 24*mm, f"{recipient} 様")

    total = int(issuance.amount)
    c.setFillColor(C_BOX)
    c.rect(x + pad, y + h - 36*mm, w - 2*pad, 10*mm, fill=1, stroke=0)
    c.setFillColor(C_BLUE)
    c.setFont(FONT_BOLD, 14)
    c.drawCentredString(x + w / 2, y + h - 30*mm, f"¥ {total:,} -")

    description = next((l.item_name for l in issuance.lines if l.item_name), "")
    c.setFillColor(black)
    c.setFont(FONT_NORMAL, 8)
    c.drawString(x + pad, y + h - 40*mm, f"但し　{description}")

    c.setStrokeColor(C_BOX)
    c.setLineWidth(0.5)
    c.line(x + pad, y + h - 43*mm, x + w - pad, y + h - 43*mm)

    cy = y + h - 47*mm
    tax10  = sum(int(l.line_total) for l in issuance.lines if l.tax_rate == 10)
    tax8   = sum(int(l.line_total) for l in issuance.lines if l.tax_rate == 8)
    exempt = sum(int(l.line_total) for l in issuance.lines if l.tax_rate in (0, -1))
    c.setFont(FONT_NORMAL, 7)
    c.setFillColor(C_GRAY)
    if tax10:
        c.drawString(x + pad, cy,
                     f"（10%対象 ¥{int(tax10/1.1):,}  消費税 ¥{tax10-int(tax10/1.1):,}）")
        cy -= 4*mm
    if tax8:
        c.drawString(x + pad, cy,
                     f"（8%対象 ¥{int(tax8/1.08):,}  消費税 ¥{tax8-int(tax8/1.08):,}）")
        cy -= 4*mm
    if exempt:
        c.drawString(x + pad, cy, f"（非課税・不課税 ¥{exempt:,}）")

    bottom_y = y + 3*mm
    c.setFillColor(black)
    c.setFont(FONT_BOLD, 9)
    c.drawString(x + pad, bottom_y + 16*mm, company.name or "")
    c.setFont(FONT_NORMAL, 7)
    c.setFillColor(C_GRAY)
    for i, line in enumerate([
        f"〒{company.postal_code}  {company.address}" if company.postal_code else company.address,
        f"TEL {company.phone}" if company.phone else "",
        f"登録番号：{company.invoice_reg_number}" if company.invoice_reg_number else "",
    ]):
        if line:
            c.drawString(x + pad, bottom_y + (10 - i*4)*mm, line)


def generate_receipt_pdf(issuance, company, output_path: str,
                          copies: int = 4) -> str:
    register_fonts()
    parent = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(parent, exist_ok=True)

    copies = max(1, min(4, copies))
    page_w, page_h = landscape(A4)
    margin = 5*mm
    gap    = 2*mm
    r_w = (page_w - 2*margin - gap) / 2
    r_h = (page_h - 2*margin - gap) / 2
    scale  = 0.92
    draw_w = r_w * scale
    draw_h = r_h * scale
    ox     = (r_w - draw_w) / 2
    oy     = (r_h - draw_h) / 2

    positions = [
        (margin + ox,             margin + r_h + gap + oy),
        (margin + ox,             margin + oy),
        (margin + r_w + gap + ox, margin + r_h + gap + oy),
        (margin + r_w + gap + ox, margin + oy),
    ]

    c = Canvas(output_path, pagesize=landscape(A4))
    c.setTitle(f"領収書_{issuance.doc_number}")

    for i in range(copies):
        px, py = positions[i]
        _draw_receipt(c, issuance, company, px, py, draw_w, draw_h)

    c.setStrokeColor(HexColor("#CCCCCC"))
    c.setLineWidth(0.3)
    c.setDash(4, 3)
    mid_x = margin + r_w + gap / 2
    mid_y = margin + r_h + gap / 2
    c.line(mid_x, margin, mid_x, page_h - margin)
    c.line(margin, mid_y, page_w - margin, mid_y)

    c.save()
    return output_path
