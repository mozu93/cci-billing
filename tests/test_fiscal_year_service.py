# tests/test_fiscal_year_service.py
from app.services.category_service import create_category
from app.services.item_template_service import create_item_template
from app.services.member_service import create_member
from app.services.project_service import (
    create_project, add_template_to_project, add_members_to_project,
    get_project_members, get_projects
)
from app.services.fiscal_year_service import rollover_fiscal_year


def _setup(db_session):
    cat = create_category(db_session, "青年部")
    tmpl = create_item_template(db_session, cat.id, "青年部会費",
                                10000, "式", 0, "invoice", "")
    proj = create_project(db_session, "2026年度 青年部会費", cat.id, 2026, "list")
    add_template_to_project(db_session, proj.id, tmpl.id)
    m1 = create_member(db_session, member_number="A-001", organization_name="○○商事",
                       organization_kana="マルマルショウジ")
    m2 = create_member(db_session, member_number="A-002", organization_name="△△産業",
                       organization_kana="サンカクサンギョウ")
    add_members_to_project(db_session, proj.id, [m1.id, m2.id])
    return proj, [m1, m2]


def test_rollover_creates_new_projects(db_session):
    proj, members = _setup(db_session)
    new_projects = rollover_fiscal_year(
        db_session, from_year=2026, to_year=2027,
        project_ids=[proj.id], keep_members={proj.id: True}
    )
    assert len(new_projects) == 1
    assert new_projects[0].fiscal_year == 2027
    assert new_projects[0].status == "draft"
    assert "2027年度" in new_projects[0].name


def test_rollover_keeps_members(db_session):
    proj, members = _setup(db_session)
    new_projects = rollover_fiscal_year(
        db_session, from_year=2026, to_year=2027,
        project_ids=[proj.id], keep_members={proj.id: True}
    )
    new_pms = get_project_members(db_session, new_projects[0].id)
    assert len(new_pms) == 2


def test_rollover_resets_members(db_session):
    proj, members = _setup(db_session)
    new_projects = rollover_fiscal_year(
        db_session, from_year=2026, to_year=2027,
        project_ids=[proj.id], keep_members={proj.id: False}
    )
    new_pms = get_project_members(db_session, new_projects[0].id)
    assert len(new_pms) == 0


def test_old_year_data_preserved(db_session):
    proj, members = _setup(db_session)
    rollover_fiscal_year(
        db_session, from_year=2026, to_year=2027,
        project_ids=[proj.id], keep_members={proj.id: True}
    )
    old_projects = get_projects(db_session, fiscal_year=2026)
    assert len(old_projects) == 1
    assert old_projects[0].fiscal_year == 2026
