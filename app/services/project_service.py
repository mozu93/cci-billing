# app/services/project_service.py
from sqlalchemy.orm import Session
from app.database.models import Project, ProjectTemplate, ProjectMember, Issuance


def create_project(session: Session, name: str, category_id: int,
                   fiscal_year: int, project_type: str,
                   notes: str = "") -> Project:
    proj = Project(
        name=name, category_id=category_id,
        fiscal_year=fiscal_year, project_type=project_type,
        status="draft", notes=notes
    )
    session.add(proj)
    session.commit()
    session.refresh(proj)
    return proj


def get_projects(session: Session, fiscal_year: int | None = None,
                 status: str | None = None) -> list[Project]:
    q = session.query(Project).filter(Project.project_type != "counter")
    if fiscal_year is not None:
        q = q.filter(Project.fiscal_year == fiscal_year)
    if status is not None:
        q = q.filter(Project.status == status)
    return q.order_by(Project.name).all()


def get_project_by_id(session: Session, project_id: int) -> Project | None:
    return session.get(Project, project_id)


def activate_project(session: Session, project_id: int) -> None:
    proj = session.get(Project, project_id)
    if proj:
        proj.status = "active"
        session.commit()


def close_project(session: Session, project_id: int) -> None:
    proj = session.get(Project, project_id)
    if proj:
        proj.status = "closed"
        session.commit()


def archive_project(session: Session, project_id: int) -> None:
    proj = session.get(Project, project_id)
    if proj:
        proj.status = "archived"
        session.commit()


def add_template_to_project(session: Session, project_id: int,
                             template_id: int,
                             unit_price_override: int | None = None,
                             sort_order: int = 0) -> ProjectTemplate:
    pt = ProjectTemplate(
        project_id=project_id,
        item_template_id=template_id,
        sort_order=sort_order,
        unit_price_override=unit_price_override
    )
    session.add(pt)
    session.commit()
    return pt


def remove_template_from_project(session: Session, project_id: int,
                                  template_id: int) -> None:
    pt = (session.query(ProjectTemplate)
          .filter_by(project_id=project_id, item_template_id=template_id)
          .first())
    if pt:
        session.delete(pt)
        session.commit()


def get_project_templates(session: Session, project_id: int) -> list[ProjectTemplate]:
    from sqlalchemy.orm import joinedload
    return (session.query(ProjectTemplate)
            .options(joinedload(ProjectTemplate.item_template))
            .filter_by(project_id=project_id)
            .order_by(ProjectTemplate.sort_order)
            .all())


def add_roster_entries(session: Session, project_id: int,
                       entries: list[dict]) -> list[ProjectMember]:
    base = session.query(ProjectMember).filter_by(project_id=project_id).count()
    pms = []
    for i, e in enumerate(entries):
        pm = ProjectMember(
            project_id=project_id,
            organization_name=e.get("organization_name", ""),
            organization_kana=e.get("organization_kana", ""),
            representative_name=e.get("representative_name", ""),
            representative_kana=e.get("representative_kana", ""),
            postal_code=e.get("postal_code", ""),
            address=e.get("address", ""),
            phone=e.get("phone", ""),
            email=e.get("email", ""),
            notes=e.get("notes", ""),
            sort_order=base + i,
        )
        session.add(pm)
        pms.append(pm)
    session.commit()
    return pms


def copy_roster_from_project(session: Session, src_project_id: int,
                             dst_project_id: int) -> list[ProjectMember]:
    src = get_project_members(session, src_project_id)
    entries = [{
        "organization_name": p.organization_name,
        "organization_kana": p.organization_kana,
        "representative_name": p.representative_name,
        "representative_kana": p.representative_kana,
        "postal_code": p.postal_code,
        "address": p.address,
        "phone": p.phone,
        "email": p.email,
        "notes": p.notes,
    } for p in src]
    return add_roster_entries(session, dst_project_id, entries)


def get_project_members(session: Session, project_id: int) -> list[ProjectMember]:
    return (session.query(ProjectMember)
            .filter_by(project_id=project_id)
            .order_by(ProjectMember.sort_order)
            .all())


def remove_member_from_project(session: Session, project_member_id: int) -> None:
    pm = session.get(ProjectMember, project_member_id)
    if pm:
        session.delete(pm)
        session.commit()


def get_project_progress(session: Session, project_id: int) -> dict:
    members = get_project_members(session, project_id)
    total = len(members)
    pm_ids = [pm.id for pm in members]
    if not pm_ids:
        return {"total": 0, "issued": 0, "paid": 0, "pending": 0}
    issued_pms = set(
        row[0] for row in
        session.query(Issuance.project_member_id)
        .filter(
            Issuance.project_member_id.in_(pm_ids),
            Issuance.status.in_(["発行済み", "支払済み"])
        ).all()
    )
    paid_pms = set(
        row[0] for row in
        session.query(Issuance.project_member_id)
        .filter(
            Issuance.project_member_id.in_(pm_ids),
            Issuance.status == "支払済み"
        ).all()
    )
    issued = len(issued_pms)
    paid = len(paid_pms)
    return {"total": total, "issued": issued, "paid": paid,
            "pending": total - issued}
