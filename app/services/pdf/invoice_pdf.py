# app/services/pdf/invoice_pdf.py
import os
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, Flowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from app.services.pdf.fonts import register_fonts, FONT_NORMAL, FONT_BOLD

C_PRIMARY     = HexColor("#1565C0")
C_HEADER_BG   = HexColor("#E3F2FD")
C_TABLE_HDR   = HexColor("#1565C0")
C_BORDER      = HexColor("#BBDEFB")
C_LIGHT_GRAY  = HexColor("#F5F5F5")
C_SUB         = HexColor("#666666")


def _date_jp(d) -> str:
    if d is None:
        return "—"
    if hasattr(d, "date"):
        d = d.date()
    return f"{d.year}年{d.month}月{d.day}日"


def _fmt(n) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "0"


def _style(name, size=11, bold=False, align=TA_LEFT, color=None, leading=None):
    register_fonts()
    return ParagraphStyle(
        name=name,
        fontName=FONT_BOLD if bold else FONT_NORMAL,
        fontSize=size,
        leading=leading or size * 1.55,
        alignment=align,
        textColor=color or black,
    )


class _FitOnePage(SimpleDocTemplate):
    """明細行が多い場合でも1ページに収まるよう自動縮小する DocTemplate"""

    def __init__(self, *args, **kwargs):
        self._fit_scale = 1.0
        super().__init__(*args, **kwargs)

    def build(self, flowables, **kw):
        import io, copy
        try:
            tall_h = A4[1] * 5
            buf = io.BytesIO()
            tmp = SimpleDocTemplate(
                buf, pagesize=(A4[0], tall_h),
                leftMargin=self.leftMargin, rightMargin=self.rightMargin,
                topMargin=self.topMargin, bottomMargin=self.bottomMargin,
            )
            tmp.build(copy.deepcopy(flowables))
            if hasattr(tmp, "frame") and tmp.frame:
                content_h = tmp.frame._y2 - tmp.frame._y
                avail_h = self.height
                if content_h > avail_h:
                    self._fit_scale = (avail_h / content_h) * 0.99
        except Exception:
            pass
        super().build(flowables, **kw)

    def _calc(self):
        super()._calc()
        s = self._fit_scale
        if s < 1.0:
            for tmpl in self.pageTemplates:
                for frame in tmpl.frames:
                    frame._x1 = self.leftMargin / s
                    frame._y1 = self.bottomMargin / s
                    frame._width = self.width / s
                    frame._height = self.height / s
                    frame._x2 = frame._x1 + frame._width
                    frame._y2 = frame._y1 + frame._height

    def handle_pageBegin(self):
        if self._fit_scale < 1.0:
            self.canv.scale(self._fit_scale, self._fit_scale)
        super().handle_pageBegin()


def generate_invoice_pdf(issuance, company, output_path: str,
                          bank_account=None, seal_image=None,
                          reissue: bool = False) -> str:
    register_fonts()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    doc = _FitOnePage(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title=f"請求書_{issuance.doc_number}",
        author=company.name if company else "",
    )
    W = A4[0] - 30*mm
    story = []

    # ── タイトル ──────────────────────────────────────
    title_text = "請　求　書（再発行）" if reissue else "請　求　書"
    story.append(Paragraph(title_text,
                            _style("title", size=20, bold=True, align=TA_CENTER,
                                   color=C_PRIMARY)))
    story.append(Spacer(1, 4*mm))

    # ── 2カラムヘッダー：宛先 ／ 発行者 ──────────────
    issue_date = issuance.issued_at
    issue_str = _date_jp(issue_date)

    client_block = _build_client_block(issuance)
    company_block = _build_company_block(issuance, company, issue_str, seal_image, W * 0.45)

    header_table = Table([[client_block, company_block]],
                          colWidths=[W * 0.55, W * 0.45])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5*mm))

    # ── ご請求金額ハイライト ──────────────────────────
    total_str = f"¥ {_fmt(issuance.amount)} -（税込）"
    total_table = Table(
        [[Paragraph("ご請求金額",
                    _style("lbl", size=14, color=black)),
          Paragraph(total_str,
                    _style("tot", size=16, bold=True, align=TA_RIGHT,
                           color=C_PRIMARY))]],
        colWidths=[52*mm, W - 52*mm]
    )
    total_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_HEADER_BG),
        ("BOX",           (0, 0), (-1, -1), 1, C_PRIMARY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4*mm),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4*mm),
        ("TOPPADDING",    (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
        ("ALIGN",         (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 5*mm))

    # ── 明細テーブル ──────────────────────────────────
    story.append(_build_line_table(issuance, W))
    story.append(Spacer(1, 5*mm))

    # ── 税額内訳 ──────────────────────────────────────
    story.append(_build_tax_summary(issuance, W))
    story.append(Spacer(1, 5*mm))

    # ── 振込先 ────────────────────────────────────────
    if bank_account and bank_account.bank_name:
        story.append(HRFlowable(width=W, thickness=0.5, color=C_BORDER))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph("振込先",
                                _style("bank_title", size=10, color=C_SUB)))
        story.append(_build_bank_block(bank_account, W))

    # インボイス制度フッター
    if company and company.invoice_reg_number:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(
            f"※ 本書は適格請求書（インボイス）です。登録番号：{company.invoice_reg_number}",
            _style("footer", size=8, color=C_SUB)
        ))

    doc.build(story)
    return output_path


# ── ブロック構築ヘルパー ───────────────────────────────

def _build_client_block(issuance) -> list:
    parts = []
    name_style = _style("cli_name", size=14)
    contact_style = _style("cli_contact", size=12)
    req_style = _style("req", size=11)

    org = issuance.recipient_organization or ""
    person = issuance.recipient_name or ""

    if person:
        parts.append(Paragraph(org, name_style))
        parts.append(Paragraph(f"{person}　様", contact_style))
    else:
        parts.append(Paragraph(f"{org}　御中" if org else "（宛名未設定）", name_style))

    parts.append(Spacer(1, 5*mm))
    parts.append(Paragraph("下記の通りご請求申し上げます。", req_style))
    return parts


def _build_company_block(issuance, company, issue_str: str,
                           seal_image=None, col_w: float = None) -> list:
    right_style = _style("co_right", size=11, align=TA_RIGHT)
    info_style  = _style("co_info",  size=11)

    co_parts = []
    if company:
        co_parts.append(Paragraph(company.name or "（自社名未設定）", info_style))
        if company.postal_code:
            co_parts.append(Paragraph(f"〒{company.postal_code}", info_style))
        if company.address:
            co_parts.append(Paragraph(company.address, info_style))
        if company.phone:
            co_parts.append(Paragraph(f"TEL:{company.phone}", info_style))

    # 印鑑がある場合は横並び
    if seal_image and getattr(seal_image, "path", None) and col_w:
        from reportlab.platypus import Image as RLImage
        seal_sz = 22*mm
        text_w = col_w - seal_sz
        try:
            seal_img = RLImage(seal_image.path, width=seal_sz, height=seal_sz)
        except Exception:
            seal_img = Spacer(seal_sz, seal_sz)
        co_block = Table([[co_parts, seal_img]], colWidths=[text_w, seal_sz])
        co_block.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        co_content = [co_block]
    else:
        co_content = list(co_parts)

    if company and company.invoice_reg_number:
        co_content.append(Paragraph(
            f"登録番号：{company.invoice_reg_number}", info_style))

    return [
        Spacer(1, 2*mm),
        Paragraph(f"NO.　{issuance.doc_number}", right_style),
        Paragraph(f"発行日　{issue_str}", right_style),
        Spacer(1, 3*mm),
        Spacer(1, 17),
    ] + co_content


def _build_line_table(issuance, W: float) -> Table:
    import html as _html
    col_widths = [W*0.45, W*0.10, W*0.07, W*0.18, W*0.20]
    headers = ["品名・摘要", "数量", "単位", "単価", "金額"]
    th_style = _style("th", size=11, bold=False, align=TA_CENTER,
                       color=white, leading=17)
    data = [[Paragraph(h, th_style) for h in headers]]

    TAX_MARKER = {0: "※非", -1: "※不", 8: "※軽"}
    nm_style   = _style("nm",    size=11, leading=17)
    num_style  = _style("num",   size=11, align=TA_RIGHT, leading=17)
    pr_style   = _style("price", size=11, align=TA_RIGHT, leading=17)

    for line in issuance.lines:
        rate = int(line.tax_rate)
        marker = TAX_MARKER.get(rate, "")
        escaped = _html.escape(str(line.item_name))
        name_xml = (f'{escaped}<font size="9" color="#C62828"> {marker}</font>'
                    if marker else escaped)
        qty = line.quantity
        qty_str = (str(int(qty)) if float(qty) == int(float(qty)) else str(qty))
        data.append([
            Paragraph(name_xml, nm_style),
            Paragraph(qty_str, num_style),
            Paragraph(line.unit or "式", nm_style),
            Paragraph(_fmt(line.unit_price), pr_style),
            Paragraph(_fmt(line.line_total), pr_style),
        ])

    total = int(issuance.amount)
    tot_lbl = _style("tot_lbl", size=11, align=TA_RIGHT, leading=17)
    tot_val = _style("tot_val", size=12, bold=True, align=TA_RIGHT,
                      leading=17, color=C_PRIMARY)
    data.append([
        Paragraph("合　計（税込）", tot_lbl), "", "", "",
        Paragraph(f"¥ {_fmt(total)}", tot_val),
    ])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_TABLE_HDR),
        ("TEXTCOLOR",     (0, 0), (-1, 0), white),
        ("GRID",          (0, 0), (-1, -1), 0.3, HexColor("#CCCCCC")),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, C_TABLE_HDR),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [white, C_LIGHT_GRAY]),
        ("BACKGROUND",    (0, -1), (-1, -1), C_HEADER_BG),
        ("SPAN",          (0, -1), (3, -1)),
        ("LINEABOVE",     (0, -1), (-1, -1), 1, C_TABLE_HDR),
        ("LEFTPADDING",   (0, 0), (-1, -1), 2*mm),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2*mm),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5*mm),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _build_tax_summary(issuance, W: float) -> Table:
    lines = issuance.lines
    tax10_incl = sum(int(l.line_total) for l in lines if int(l.tax_rate) == 10)
    tax8_incl  = sum(int(l.line_total) for l in lines if int(l.tax_rate) == 8)
    exempt     = sum(int(l.line_total) for l in lines if int(l.tax_rate) == 0)
    non_tax    = sum(int(l.line_total) for l in lines if int(l.tax_rate) == -1)
    tax10_amt  = int(tax10_incl * 10 / 110)
    tax8_amt   = int(tax8_incl  *  8 / 108)
    tax_total  = tax10_amt + tax8_amt

    rows = []
    if tax10_incl:
        rows.append(["10%対象", _fmt(tax10_incl), _fmt(tax10_amt)])
    if tax8_incl:
        rows.append(["8%対象（※軽）", _fmt(tax8_incl), _fmt(tax8_amt)])
    if exempt:
        rows.append(["非課税（※非）", _fmt(exempt), "—"])
    if non_tax:
        rows.append(["不課税（※不）", _fmt(non_tax), "—"])
    rows.append(["消費税合計", "", _fmt(tax_total)])

    sm_style = _style("sm", size=11, leading=17)
    rv_style = _style("rv", size=11, align=TA_RIGHT, leading=17)
    inner_col = [W*0.30, W*0.20, W*0.20]
    inner_data = [[Paragraph(r[0], sm_style),
                   Paragraph(r[1], rv_style),
                   Paragraph(r[2], rv_style)] for r in rows]
    inner_tbl = Table(inner_data, colWidths=inner_col)
    inner_tbl.setStyle(TableStyle([
        ("GRID",          (0, 0), (-1, -1), 0.3, HexColor("#CCCCCC")),
        ("BACKGROUND",    (0, -1), (-1, -1), C_HEADER_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5*mm),
        ("LEFTPADDING",   (0, 0), (-1, -1), 2*mm),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2*mm),
    ]))

    legend_parts = []
    if tax8_incl:  legend_parts.append("※軽＝軽減税率(8%)")
    if exempt:     legend_parts.append("※非＝非課税")
    if non_tax:    legend_parts.append("※不＝不課税")
    note = (Paragraph("　".join(legend_parts),
                       _style("note", size=9, color=C_SUB))
            if legend_parts else Spacer(1, 0))

    outer = Table([[Spacer(1, 0), note, inner_tbl]],
                   colWidths=[W*0.30, W*0.00, W*0.70])
    outer.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    return outer


def _build_bank_block(ba, W: float) -> Table:
    info_style = _style("bank_info", size=11, leading=16)
    rows = []
    label = f"銀行名：{ba.bank_name}"
    if ba.bank_branch:
        label += f"　{ba.bank_branch}"
    rows.append([Paragraph(label, info_style)])
    if ba.bank_account_type and ba.bank_account_number:
        rows.append([Paragraph(
            f"口座番号：{ba.bank_account_type}　{ba.bank_account_number}", info_style)])
    if ba.bank_account_name:
        rows.append([Paragraph(f"口座名義：{ba.bank_account_name}", info_style)])
    tbl = Table(rows, colWidths=[W*0.6], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5*mm),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
    ]))
    return tbl
