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


# A4キュー — ORM オブジェクトはセッション跨ぎでデタッチするため ID のみ保持
_a4_queue: list[int] = []


def generate_and_open(issuance, session, receipt_fmt: str = "a5",
                      reissue: bool = False) -> str | None:
    """
    receipt_fmt: "a5" → A5縦1事業所（原本+控え）
                 "a4" → A4横2事業所キュー方式
    """
    company, bank = get_company_and_bank(session)
    if not company:
        return None
    seal = get_default_seal(session, company)
    output_dir = get_pdf_output_dir()

    suffix = "_再発行" if reissue else ""
    if issuance.doc_type == "invoice":
        path = os.path.join(output_dir, f"{issuance.doc_number}{suffix}.pdf")
        from app.services.pdf.invoice_pdf import generate_invoice_pdf
        generate_invoice_pdf(issuance, company, path, bank,
                             seal_image=seal, reissue=reissue)
        issuance.pdf_path = path
        session.commit()
        from app.services.print_service import open_pdf
        open_pdf(path)
        return path

    # 領収書
    if receipt_fmt == "a4":
        return _generate_a4_queued(issuance.id, session, company, seal, output_dir,
                                   reissue=reissue)
    else:
        path = os.path.join(output_dir, f"{issuance.doc_number}{suffix}.pdf")
        from app.services.pdf.receipt_pdf import generate_receipt_pdf
        generate_receipt_pdf(issuance, company, path,
                             seal_image=seal, reissue=reissue)
        issuance.pdf_path = path
        session.commit()
        from app.services.print_service import open_pdf
        open_pdf(path)
        return path


def _load_issuance(session, issuance_id: int):
    from app.database.models import Issuance, IssuanceLine
    from sqlalchemy.orm import joinedload
    return (session.query(Issuance)
            .options(joinedload(Issuance.lines))
            .filter_by(id=issuance_id)
            .first())


def _generate_a4_queued(issuance_id: int, session, company, seal, output_dir,
                        reissue: bool = False) -> str | None:
    """1件目はIDのみキュー保持。2件目が来たら両方リロードしてA4印刷。"""
    global _a4_queue
    _a4_queue.append(issuance_id)

    if len(_a4_queue) < 2:
        return None   # 呼び出し元でメッセージ表示

    id1, id2 = _a4_queue[0], _a4_queue[1]
    _a4_queue = []

    iss1 = _load_issuance(session, id1)
    iss2 = _load_issuance(session, id2)
    suffix = "_再発行" if reissue else ""
    path = os.path.join(output_dir, f"A4_{iss1.doc_number}_{iss2.doc_number}{suffix}.pdf")
    from app.services.pdf.receipt_pdf import generate_receipt_pdf_a4
    generate_receipt_pdf_a4([iss1, iss2], company, path,
                             seal_image=seal, reissue=reissue)
    iss1.pdf_path = path
    iss2.pdf_path = path
    session.commit()
    from app.services.print_service import open_pdf
    open_pdf(path)
    return path


def flush_a4_queue(session) -> str | None:
    """キューに1件残っている場合、単独でA4左半分に印刷して出力する。"""
    global _a4_queue
    if not _a4_queue:
        return None
    issuance_id = _a4_queue[0]
    _a4_queue = []

    iss = _load_issuance(session, issuance_id)
    from app.database.models import CompanySettings
    company = session.query(CompanySettings).first()
    seal = get_default_seal(session, company)
    output_dir = get_pdf_output_dir()
    path = os.path.join(output_dir, f"A4_{iss.doc_number}.pdf")
    from app.services.pdf.receipt_pdf import generate_receipt_pdf_a4
    generate_receipt_pdf_a4([iss], company, path, seal_image=seal)
    iss.pdf_path = path
    session.commit()
    from app.services.print_service import open_pdf
    open_pdf(path)
    return path


def get_a4_queue_count() -> int:
    return len(_a4_queue)


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
