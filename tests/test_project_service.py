# tests/test_project_service.py
from app.services.category_service import create_category
from app.services.item_template_service import create_item_template
from app.services.member_service import create_member
from app.services.project_service import (
    create_project, get_projects, activate_project, close_project,
    add_template_to_project, add_members_to_project,
    get_project_members, get_project_progress
)


def test_create_project(db_session):
    cat = create_category(db_session, "青年部")
    proj = create_project(db_session, name="2026年度 青年部会費",
                          category_id=cat.id, fiscal_year=2026,
                          project_type="list")
    assert proj.id is not None
    assert proj.status == "draft"
    assert proj.fiscal_year == 2026


def test_activate_project(db_session):
    cat = create_category(db_session, "青年部")
    proj = create_project(db_session, "2026年度 青年部会費", cat.id, 2026, "list")
    activate_project(db_session, proj.id)
    db_session.refresh(proj)
    assert proj.status == "active"


def test_get_projects_by_year(db_session):
    cat = create_category(db_session, "青年部")
    create_project(db_session, "2026年度 青年部会費", cat.id, 2026, "list")
    create_project(db_session, "2025年度 青年部会費", cat.id, 2025, "list")
    result = get_projects(db_session, fiscal_year=2026)
    assert len(result) == 1
    assert result[0].fiscal_year == 2026


def test_add_template_to_project(db_session):
    cat = create_category(db_session, "青年部")
    tmpl = create_item_template(db_session, cat.id, "青年部会費", 10000, "式", 0, "invoice", "")
    proj = create_project(db_session, "2026年度 青年部会費", cat.id, 2026, "list")
    add_template_to_project(db_session, proj.id, tmpl.id)
    from app.database.models import ProjectTemplate
    pts = db_session.query(ProjectTemplate).filter_by(project_id=proj.id).all()
    assert len(pts) == 1
    assert pts[0].item_template_id == tmpl.id


def test_add_members_to_project(db_session):
    cat = create_category(db_session, "青年部")
    proj = create_project(db_session, "2026年度 青年部会費", cat.id, 2026, "list")
    m1 = create_member(db_session, member_number="A-001", organization_name="○○商事",
                       organization_kana="マルマルショウジ")
    m2 = create_member(db_session, member_number="A-002", organization_name="△△産業",
                       organization_kana="サンカクサンギョウ")
    add_members_to_project(db_session, proj.id, [m1.id, m2.id])
    members = get_project_members(db_session, proj.id)
    assert len(members) == 2


def test_get_project_progress(db_session):
    cat = create_category(db_session, "青年部")
    proj = create_project(db_session, "2026年度 青年部会費", cat.id, 2026, "list")
    m1 = create_member(db_session, member_number="A-001", organization_name="○○商事",
                       organization_kana="マルマルショウジ")
    m2 = create_member(db_session, member_number="A-002", organization_name="△△産業",
                       organization_kana="サンカクサンギョウ")
    add_members_to_project(db_session, proj.id, [m1.id, m2.id])
    progress = get_project_progress(db_session, proj.id)
    assert progress["total"] == 2
    assert progress["issued"] == 0
    assert progress["paid"] == 0
    assert progress["pending"] == 2
