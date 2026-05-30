# app/services/issuance_service.py
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.database.models import (
    Issuance, IssuanceLine, Payment, ProjectTemplate, ProjectMember, Member
)


def get_next_doc_number(session: Session, doc_type: str,
                         fiscal_year: int, month: int) -> str:
    prefix = "INV" if doc_type == "invoice" else "RCP"
    ym = f"{fiscal_year}{month:02d}"
    pattern = f"{prefix}-{ym}-%"
    last = (session.query(Issuance)
            .filter(Issuance.doc_number.like(pattern))
            .order_by(Issuance.doc_number.desc())
            .first())
    if last:
        seq = int(last.doc_number.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}-{ym}-{seq:04d}"


def _build_lines_from_project(session: Session, project_id: int,
                               quantity: int = 1) -> tuple[list[dict], int]:
    pts = (session.query(ProjectTemplate)
           .filter_by(project_id=project_id)
           .order_by(ProjectTemplate.sort_order)
           .all())
    lines = []
    total = 0
    for pt in pts:
        tmpl = pt.item_template
        price = int(pt.unit_price_override or tmpl.unit_price)
        line_total = price * quantity
        total += line_total
        lines.append({
            "item_template_id": tmpl.id,
            "item_name": tmpl.name,
            "quantity": quantity,
            "unit": tmpl.unit,
            "unit_price": price,
            "tax_rate": tmpl.tax_rate,
            "line_total": line_total,
        })
    return lines, total


def create_issuance_for_member(session: Session, project_id: int,
                                project_member_id: int, member: Member,
                                doc_type: str, fiscal_year: int,
                                month: int) -> Issuance:
    doc_number = get_next_doc_number(session, doc_type, fiscal_year, month)
    lines, total = _build_lines_from_project(session, project_id)

    issuance = Issuance(
        project_id=project_id,
        project_member_id=project_member_id,
        recipient_organization=member.organization_name,
        recipient_name=member.representative_name,
        doc_type=doc_type,
        doc_number=doc_number,
        status="準備中",
        amount=total,
    )
    session.add(issuance)
    session.flush()
    for line_data in lines:
        session.add(IssuanceLine(issuance_id=issuance.id, **line_data))
    session.commit()
    session.refresh(issuance)
    return issuance


def create_counter_issuance(session: Session, project_id: int,
                             recipient_organization: str,
                             recipient_name: str,
                             doc_type: str, quantity: int,
                             fiscal_year: int, month: int) -> Issuance:
    doc_number = get_next_doc_number(session, doc_type, fiscal_year, month)
    lines, total = _build_lines_from_project(session, project_id, quantity)
    now = datetime.now()
    issuance = Issuance(
        project_id=project_id,
        project_member_id=None,
        recipient_organization=recipient_organization,
        recipient_name=recipient_name,
        doc_type=doc_type,
        doc_number=doc_number,
        status="発行済み",
        amount=total,
        issued_at=now,
    )
    session.add(issuance)
    session.flush()
    for line_data in lines:
        session.add(IssuanceLine(issuance_id=issuance.id, **line_data))
    session.commit()
    session.refresh(issuance)
    return issuance


def create_combined_issuance(session: Session,
                              issuances_data: list[dict],
                              doc_type: str,
                              recipient_organization: str,
                              recipient_name: str,
                              fiscal_year: int, month: int,
                              staff_id: int | None,
                              staff_name: str,
                              delivery_method: str) -> Issuance:
    doc_number = get_next_doc_number(session, doc_type, fiscal_year, month)
    all_lines = []
    total = 0
    primary_project_id = issuances_data[0]["project_id"] if issuances_data else None
    for data in issuances_data:
        lines, sub_total = _build_lines_from_project(
            session, data["project_id"], data.get("quantity", 1))
        all_lines.extend(lines)
        total += sub_total
    now = datetime.now()
    issuance = Issuance(
        project_id=primary_project_id,
        project_member_id=None,
        recipient_organization=recipient_organization,
        recipient_name=recipient_name,
        doc_type=doc_type,
        doc_number=doc_number,
        status="発行済み",
        amount=total,
        issued_at=now,
        staff_id=staff_id,
        staff_name=staff_name,
        delivery_method=delivery_method,
    )
    session.add(issuance)
    session.flush()
    for line_data in all_lines:
        session.add(IssuanceLine(issuance_id=issuance.id, **line_data))
    for data in issuances_data:
        pm_id = data.get("project_member_id")
        if pm_id:
            prep = (session.query(Issuance)
                    .filter_by(project_member_id=pm_id, status="準備中")
                    .first())
            if prep:
                prep.status = "発行済み"
                prep.issued_at = now
                prep.staff_name = staff_name
    session.commit()
    session.refresh(issuance)
    return issuance


def mark_as_issued(session: Session, issuance_id: int,
                   staff_id: int | None, staff_name: str,
                   delivery_method: str = "窓口手渡し") -> None:
    issuance = session.get(Issuance, issuance_id)
    if issuance:
        issuance.status = "発行済み"
        issuance.issued_at = datetime.now()
        issuance.staff_id = staff_id
        issuance.staff_name = staff_name
        issuance.delivery_method = delivery_method
        session.commit()


def record_payment(session: Session, issuance_id: int,
                   payment_date: date, amount: int,
                   payment_method: str = "現金",
                   staff_id: int | None = None,
                   staff_name: str = "",
                   notes: str = "") -> None:
    issuance = session.get(Issuance, issuance_id)
    if not issuance:
        return
    payment = Payment(
        issuance_id=issuance_id,
        payment_date=payment_date,
        amount=amount,
        payment_method=payment_method,
        staff_id=staff_id,
        staff_name=staff_name,
        notes=notes,
    )
    session.add(payment)
    issuance.status = "支払済み"
    session.commit()


def get_pending_issuances_for_member(session: Session,
                                     member_id: int) -> list[Issuance]:
    pm_ids = [pm.id for pm in
              session.query(ProjectMember).filter_by(member_id=member_id).all()]
    if not pm_ids:
        return []
    return (session.query(Issuance)
            .filter(Issuance.project_member_id.in_(pm_ids),
                    Issuance.status == "準備中")
            .all())


def get_project_issuances(session: Session, project_id: int,
                           status: str | None = None) -> list[Issuance]:
    q = session.query(Issuance).filter_by(project_id=project_id)
    if status:
        q = q.filter(Issuance.status == status)
    return q.order_by(Issuance.created_at.desc()).all()
