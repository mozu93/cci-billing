# app/services/pdf/batch_pdf.py
import os
from datetime import date
from app.services.pdf.invoice_pdf import generate_invoice_pdf
from app.services.pdf.receipt_pdf import generate_receipt_pdf
from app.services.project_service import get_project_members
from app.services.issuance_service import create_issuance_for_member
from app.database.models import Issuance, CompanySettings, BankAccount, ProjectTemplate


def generate_batch_pdf(session, project_id: int, company: CompanySettings,
                        output_dir: str,
                        bank_account: BankAccount | None = None) -> list[str]:
    pt = session.query(ProjectTemplate).filter_by(project_id=project_id).first()
    doc_type = ("receipt"
                if pt and pt.item_template.doc_type == "receipt"
                else "invoice")

    os.makedirs(output_dir, exist_ok=True)
    pms = get_project_members(session, project_id)
    today = date.today()
    generated = []

    for pm in pms:
        iss = (session.query(Issuance)
               .filter_by(project_member_id=pm.id)
               .order_by(Issuance.created_at.desc())
               .first())
        if iss is None:
            m = pm.member
            if not m:
                continue
            iss = create_issuance_for_member(
                session, project_id=project_id,
                project_member_id=pm.id,
                member=m, doc_type=doc_type,
                fiscal_year=today.year, month=today.month
            )
        path = os.path.join(output_dir, f"{iss.doc_number}.pdf")
        if doc_type == "invoice":
            generate_invoice_pdf(iss, company, path, bank_account)
        else:
            generate_receipt_pdf(iss, company, path)
        iss.pdf_path = path
        session.commit()
        generated.append(path)

    return generated
