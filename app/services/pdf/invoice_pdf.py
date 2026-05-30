# app/services/pdf/invoice_pdf.py
import os
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from app.services.pdf.fonts import register_fonts, FONT_NORMAL, FONT_BOLD

C_BLUE   = HexColor("#1E40AF")
C_LIGHT  = HexColor("#EFF6FF")
C_GRAY   = HexColor("#F8FAFC")
C_BORDER = HexColor("#CBD5E1")
C_TEXT   = HexColor("#1E293B")
C_SUB    = HexColor("#64748B")


def _style(name, font=None, size=10, leading=None, alignment=TA_LEFT,
           color=None, bold=False):
    register_fonts()
    f = font or (FONT_BOLD if bold else FONT_NORMAL)
    return ParagraphStyle(
        name=name, fontName=f, fontSize=size,
        leading=leading or size * 1.4,
        alignment=alignment,
        textColor=color or C_TEXT,
    )


def generate_invoice_pdf(issuance, company, output_path: str,
                          bank_account=None, seal_path: str | None = None) -> str:
    register_fonts()
    parent = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(parent, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    W = A4[0] - 30*mm
    story = []

    # タイトル
    story.append(Paragraph(
        "請　求　書",
        _style("title", size=20, bold=True, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 4*mm))

    # 発行番号・日付
    issue_date = getattr(issuance, 'issued_at', None)
    date_str = (issue_date.strftime("%Y年%m月%d日") if issue_date
                else date.today().strftime("%Y年%m月%d日"))
    info_data = [["発行番号：", issuance.doc_number, "発行日：", date_str]]
    info_table = Table(info_data, colWidths=[25*mm, 60*mm, 20*mm, 50*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), FONT_NORMAL),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (-1,-1), C_SUB),
        ("VALIGN",   (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4*mm))

    # 宛先 + 発行元
    recipient = ((issuance.recipient_organization or "") +
                 (f" {issuance.recipient_name}" if issuance.recipient_name else "")).strip() or "　"
    issuer_lines = [company.name or ""]
    if company.postal_code:
        issuer_lines.append(f"〒{company.postal_code}")
    if company.address:
        issuer_lines.append(company.address)
    if company.phone:
        issuer_lines.append(f"TEL {company.phone}")
    if company.invoice_reg_number:
        issuer_lines.append(f"登録番号：{company.invoice_reg_number}")

    addr_data = [[
        Paragraph(f"{recipient} 御中", _style("addr", size=13, bold=True)),
        Paragraph("<br/>".join(l for l in issuer_lines if l),
                  _style("issuer", size=8, alignment=TA_RIGHT, color=C_SUB))
    ]]
    addr_table = Table(addr_data, colWidths=[W*0.55, W*0.45])
    addr_table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "BOTTOM")]))
    story.append(addr_table)
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width=W, color=C_BLUE, thickness=2))
    story.append(Spacer(1, 3*mm))

    # 合計金額
    total = int(issuance.amount)
    story.append(Paragraph(
        f"ご請求金額：<b>¥{total:,}</b>（税込）",
        _style("total", size=14, bold=True, color=C_BLUE)
    ))
    story.append(Spacer(1, 4*mm))

    # 明細テーブル
    header = ["品目・摘要", "数量", "単位", "単価", "金額", "税率"]
    rows = [header]
    for line in issuance.lines:
        tax_label = {10: "10%", 8: "8%", 0: "非課税", -1: "不課税"}.get(
            line.tax_rate, f"{line.tax_rate}%")
        rows.append([
            line.item_name,
            str(int(line.quantity)),
            line.unit,
            f"¥{int(line.unit_price):,}",
            f"¥{int(line.line_total):,}",
            tax_label,
        ])

    col_w = [W*0.38, W*0.08, W*0.08, W*0.14, W*0.14, W*0.08]
    detail_table = Table(rows, colWidths=col_w, repeatRows=1)
    detail_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), C_BLUE),
        ("TEXTCOLOR",   (0,0), (-1,0), white),
        ("FONTNAME",    (0,0), (-1,0), FONT_BOLD),
        ("FONTNAME",    (0,1), (-1,-1), FONT_NORMAL),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ALIGN",       (1,0), (-1,-1), "CENTER"),
        ("ALIGN",       (3,1), (4,-1), "RIGHT"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, C_GRAY]),
        ("GRID",        (0,0), (-1,-1), 0.5, C_BORDER),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 3*mm))

    # 税率別小計
    tax10_base = sum(int(l.unit_price)*int(l.quantity) for l in issuance.lines if l.tax_rate == 10)
    tax8_base  = sum(int(l.unit_price)*int(l.quantity) for l in issuance.lines if l.tax_rate == 8)
    exempt     = sum(int(l.line_total) for l in issuance.lines if l.tax_rate == 0)
    non_tax    = sum(int(l.line_total) for l in issuance.lines if l.tax_rate == -1)

    subtotal_rows = [["", "小計", "消費税", "合計"]]
    if tax10_base:
        subtotal_rows.append(["10%対象", f"¥{tax10_base:,}",
                               f"¥{int(tax10_base*0.1):,}",
                               f"¥{int(tax10_base*1.1):,}"])
    if tax8_base:
        subtotal_rows.append(["8%対象", f"¥{tax8_base:,}",
                               f"¥{int(tax8_base*0.08):,}",
                               f"¥{int(tax8_base*1.08):,}"])
    if exempt:
        subtotal_rows.append(["非課税", f"¥{exempt:,}", "—", f"¥{exempt:,}"])
    if non_tax:
        subtotal_rows.append(["不課税", f"¥{non_tax:,}", "—", f"¥{non_tax:,}"])
    subtotal_rows.append(["合計", "", "", f"¥{total:,}"])

    sub_col_w = [W*0.2, W*0.2, W*0.2, W*0.2]
    sub_table = Table(subtotal_rows, colWidths=sub_col_w)
    sub_table.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,-1), FONT_NORMAL),
        ("FONTNAME",  (0,0), (-1,0), FONT_BOLD),
        ("FONTNAME",  (0,-1), (-1,-1), FONT_BOLD),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("ALIGN",     (1,0), (-1,-1), "RIGHT"),
        ("GRID",      (0,0), (-1,-1), 0.5, C_BORDER),
        ("BACKGROUND", (0,0), (-1,0), C_LIGHT),
        ("BACKGROUND", (0,-1), (-1,-1), C_LIGHT),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    right_data = [["", sub_table]]
    right_table = Table(right_data, colWidths=[W*0.2, W*0.8])
    right_table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(right_table)
    story.append(Spacer(1, 4*mm))

    # 振込先
    if bank_account:
        story.append(HRFlowable(width=W, color=C_BORDER, thickness=0.5))
        story.append(Spacer(1, 2*mm))
        for line in [
            f"【振込先】 {bank_account.bank_name} {bank_account.bank_branch}",
            f"　{bank_account.bank_account_type}　{bank_account.bank_account_number}",
            f"　口座名義：{bank_account.bank_account_name}",
        ]:
            story.append(Paragraph(line, _style("bank", size=9, color=C_SUB)))

    # インボイスフッター
    if company.invoice_reg_number:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(
            f"※ 本書は適格請求書（インボイス）です。登録番号：{company.invoice_reg_number}",
            _style("footer", size=7, color=C_SUB)
        ))

    doc.build(story)
    return output_path
