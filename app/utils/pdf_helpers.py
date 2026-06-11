# app/utils/pdf_helpers.py
import os
from app.database.models import CompanySettings, BankAccount


def get_company_and_bank(session) -> tuple:
    company = session.query(CompanySettings).first()
    bank = None
    if company:
        bank = (session.query(BankAccount)
                .filter_by(company_id=company.id, is_default=True)
                .first()
                or session.query(BankAccount)
                .filter_by(company_id=company.id)
                .first())
    return company, bank


def get_pdf_output_dir() -> str:
    from app.utils.app_config import get_config
    config = get_config()
    base = config.get("pdf_output_dir", "")
    if not base:
        base = os.path.join(os.path.expanduser("~"), "cci-billing", "pdf")
    os.makedirs(base, exist_ok=True)
    return base


def get_default_seal(session, company):
    if company is None:
        return None
    if not getattr(company, "print_seal", True):
        return None
    from app.database.models import SealImage
    seal = (session.query(SealImage)
            .filter_by(company_id=company.id, is_default=True)
            .first()
            or session.query(SealImage)
            .filter_by(company_id=company.id)
            .first())
    return seal


def generate_and_open(issuance, session, reissue: bool = False,
                      due_date=None, open_file: bool = True) -> str | None:
    """発行データのPDFを生成し、open_file=True ならビューアで開く。

    一括発行時は open_file=False で生成だけ行い、
    呼び出し元で merge_and_open() にまとめて渡す。
    """
    company, bank = get_company_and_bank(session)
    if not company:
        return None
    seal = get_default_seal(session, company)
    output_dir = get_pdf_output_dir()

    from app.utils.app_config import get_config
    _cfg = get_config()
    _window_envelope = _cfg.get("window_envelope", False)

    suffix = "_再発行" if reissue else ""
    if issuance.doc_type == "invoice":
        path = os.path.join(output_dir, f"{issuance.doc_number}{suffix}.pdf")
        from app.services.pdf.invoice_pdf import generate_invoice_pdf
        postal_code = address = address2 = ""
        if _window_envelope and issuance.project_member_id:
            from app.database.models import ProjectMember
            pm = session.get(ProjectMember, issuance.project_member_id)
            if pm:
                postal_code = pm.postal_code or ""
                address = pm.address or ""
                address2 = pm.address2 or ""
        subject = ""
        proj_notes = ""
        if issuance.project_id:
            from app.database.models import Project
            proj = session.get(Project, issuance.project_id)
            if proj:
                subject = proj.name or ""
                if due_date is None:
                    due_date = proj.due_date
                proj_notes = proj.notes or ""
        generate_invoice_pdf(issuance, company, path, bank,
                             seal_image=seal, reissue=reissue,
                             window_envelope=_window_envelope,
                             recipient_postal_code=postal_code,
                             recipient_address=address,
                             recipient_address2=address2,
                             subject=subject,
                             due_date=due_date,  # None → invoice_pdf側で翌月末自動設定
                             notes=proj_notes)
        issuance.pdf_path = path
        session.commit()
        if open_file:
            from app.services.print_service import open_pdf
            open_pdf(path)
        return path

    # 領収書（A5縦・原本+控え）
    path = os.path.join(output_dir, f"{issuance.doc_number}{suffix}.pdf")
    from app.services.pdf.receipt_pdf import generate_receipt_pdf
    generate_receipt_pdf(issuance, company, path,
                         seal_image=seal, reissue=reissue)
    issuance.pdf_path = path
    session.commit()
    if open_file:
        from app.services.print_service import open_pdf
        open_pdf(path)
    return path


def merge_and_open(paths: list[str], base_name: str) -> str | None:
    """複数PDFを1ファイルに結合して開く（連続印刷用）。

    pypdf が無い環境では結合せず出力フォルダを開く。
    返り値は結合PDFのパス（フォルダを開いた場合は None）。
    """
    paths = [p for p in paths if p and os.path.exists(p)]
    if not paths:
        return None
    output_dir = get_pdf_output_dir()
    from app.services.print_service import open_pdf
    try:
        from pypdf import PdfWriter
    except ImportError:
        # 結合ライブラリ未導入: フォルダを開くだけにフォールバック
        os.startfile(output_dir)
        return None
    from datetime import datetime
    safe = "".join(c for c in base_name if c not in '\\/:*?"<>|')
    merged = os.path.join(
        output_dir,
        f"{safe}_一括_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    writer = PdfWriter()
    for p in paths:
        writer.append(p)
    with open(merged, "wb") as f:
        writer.write(f)
    writer.close()
    open_pdf(merged)
    return merged


def build_preview_issuance(lines_data: list[dict], doc_type: str):
    """宛先空のプレビュー用 Issuance（セッション未追加・非永続）を組み立てる。"""
    from datetime import datetime
    from app.database.models import Issuance, IssuanceLine
    lines = []
    total = 0
    for ld in lines_data:
        line_total = int(ld["unit_price"]) * int(ld["quantity"])
        total += line_total
        lines.append(IssuanceLine(
            item_template_id=ld.get("item_template_id"),
            item_name=ld["item_name"],
            quantity=ld["quantity"],
            unit=ld["unit"],
            unit_price=ld["unit_price"],
            tax_rate=ld["tax_rate"],
            line_total=line_total,
        ))
    return Issuance(
        project_id=None, project_member_id=None,
        recipient_organization="", recipient_name="",
        doc_type=doc_type, doc_number="（プレビュー）",
        status="プレビュー", amount=total,
        issued_at=datetime.now(), lines=lines,
    )


def generate_preview(lines_data: list[dict], doc_type: str, session) -> str | None:
    """プレビュー用PDFを一時ファイルに生成して開く（DBには書き込まない）。"""
    import os
    company, bank = get_company_and_bank(session)
    if not company:
        return None
    seal = get_default_seal(session, company)
    output_dir = get_pdf_output_dir()
    path = os.path.join(output_dir, "_preview.pdf")
    issuance = build_preview_issuance(lines_data, doc_type)
    if doc_type == "invoice":
        from app.services.pdf.invoice_pdf import generate_invoice_pdf
        generate_invoice_pdf(issuance, company, path, bank, seal_image=seal)
    else:
        from app.services.pdf.receipt_pdf import generate_receipt_pdf
        generate_receipt_pdf(issuance, company, path, seal_image=seal)
    from app.services.print_service import open_pdf
    open_pdf(path)
    return path
