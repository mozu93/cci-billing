# tests/test_project_service.py
from app.services.category_service import create_category
from app.services.item_template_service import create_item_template
from app.services.project_service import (
    create_project, get_projects, activate_project, close_project,
    add_template_to_project, add_roster_entries,
    get_project_members, get_project_progress, remove_member_from_project,
    copy_roster_from_project, get_project_by_id,
)


def test_create_project(db_session):
    cat = create_category(db_session, "青年部")
    proj = create_project(db_session, name="2026年度 青年部会費",
                          category_id=cat.id, fiscal_year=2026,
                          project_type="list")
    assert proj.id is not None
    assert proj.status == "active"
    assert proj.fiscal_year == 2026


def test_create_project_is_active(db_session):
    from app.services.project_service import create_project
    p = create_project(db_session, name="2026 青年部", category_id=None,
                       fiscal_year=2026, project_type="list")
    assert p.status == "active"


def test_reopen_project(db_session):
    from app.services.project_service import create_project, close_project, reopen_project, get_project_by_id
    p = create_project(db_session, name="x", category_id=None, fiscal_year=2026, project_type="list")
    close_project(db_session, p.id)
    assert get_project_by_id(db_session, p.id).status == "closed"
    reopen_project(db_session, p.id)
    assert get_project_by_id(db_session, p.id).status == "active"


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


def _mk_project(session, name="2026 青年部"):
    return create_project(session, name=name, category_id=None,
                          fiscal_year=2026, project_type="list")


def test_add_roster_entries_and_get(db_session):
    proj = _mk_project(db_session)
    add_roster_entries(db_session, proj.id, [
        {"organization_name": "○○商事", "representative_name": "田中"},
        {"organization_name": "△△産業", "representative_name": "鈴木",
         "email": "suzuki@example.com"},
    ])
    pms = get_project_members(db_session, proj.id)
    assert [p.organization_name for p in pms] == ["○○商事", "△△産業"]
    assert pms[1].email == "suzuki@example.com"
    assert pms[0].sort_order == 0 and pms[1].sort_order == 1


def test_copy_roster_from_project_snapshot(db_session):
    src = _mk_project(db_session, "2025 青年部")
    add_roster_entries(db_session, src.id, [
        {"organization_name": "○○商事", "representative_name": "田中"},
    ])
    dst = _mk_project(db_session, "2026 青年部")
    copy_roster_from_project(db_session, src.id, dst.id)
    dst_pms = get_project_members(db_session, dst.id)
    assert len(dst_pms) == 1
    assert dst_pms[0].organization_name == "○○商事"
    dst_pms[0].organization_name = "改名"
    db_session.commit()
    src_pms = get_project_members(db_session, src.id)
    assert src_pms[0].organization_name == "○○商事"


def test_get_project_progress(db_session):
    proj = _mk_project(db_session)
    add_roster_entries(db_session, proj.id, [
        {"organization_name": "○○商事", "representative_name": "田中"},
        {"organization_name": "△△産業", "representative_name": "鈴木"},
    ])
    progress = get_project_progress(db_session, proj.id)
    assert progress["total"] == 2
    assert progress["issued"] == 0
    assert progress["paid"] == 0
    assert progress["pending"] == 2
