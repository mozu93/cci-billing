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
    q = session.query(Project)
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


def add_members_to_project(session: Session, project_id: int,
                            member_ids: list[int]) -> list[ProjectMember]:
    existing = {pm.member_id for pm in
                session.query(ProjectMember).filter_by(project_id=project_id).all()}
    pms = []
    for i, mid in enumerate(member_ids):
        if mid in existing:
            continue
        pm = ProjectMember(project_id=project_id, member_id=mid, sort_order=i)
        session.add(pm)
        pms.append(pm)
    session.commit()
    return pms


def get_project_members(session: Session, project_id: int) -> list[ProjectMember]:
    from sqlalchemy.orm import joinedload
    return (session.query(ProjectMember)
            .options(joinedload(ProjectMember.member))
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
