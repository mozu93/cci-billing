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


def generate_and_open(issuance, session) -> str | None:
    company, bank = get_company_and_bank(session)
    if not company:
        return None
    output_dir = get_pdf_output_dir()
    path = os.path.join(output_dir, f"{issuance.doc_number}.pdf")
    if issuance.doc_type == "invoice":
        from app.services.pdf.invoice_pdf import generate_invoice_pdf
        generate_invoice_pdf(issuance, company, path, bank)
    else:
        from app.services.pdf.receipt_pdf import generate_receipt_pdf
        generate_receipt_pdf(issuance, company, path)
    issuance.pdf_path = path
    session.commit()
    from app.services.print_service import open_pdf
    open_pdf(path)
    return path
