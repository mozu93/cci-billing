# tests/test_issuance_service.py
from datetime import date
from app.services.category_service import create_category
from app.services.item_template_service import create_item_template
from app.services.project_service import (
    create_project, add_template_to_project, add_roster_entries,
    get_project_members
)
from app.services.issuance_service import (
    get_next_doc_number, create_issuance_for_member,
    create_counter_issuance, mark_as_issued, record_payment,
    get_pending_issuances_for_project_member, get_project_issuances
)


def _setup(db_session):
    cat = create_category(db_session, "青年部")
    tmpl = create_item_template(db_session, cat.id, "青年部会費",
                                10000, "式", 0, "invoice", "")
    proj = create_project(db_session, "2026年度 青年部会費", cat.id, 2026, "list")
    add_template_to_project(db_session, proj.id, tmpl.id)
    add_roster_entries(db_session, proj.id, [
        {"organization_name": "○○商事", "representative_name": "田中太郎"},
    ])
    pm = get_project_members(db_session, proj.id)[0]
    return proj, tmpl, pm


def test_get_next_doc_number(db_session):
    n1 = get_next_doc_number(db_session, "invoice", 2026, 5)
    n2 = get_next_doc_number(db_session, "invoice", 2026, 5)
    assert n1 == "INV-202605-0001"
    assert n2 == "INV-202605-0001"  # まだ保存されていないので同じ番号


def test_get_next_doc_number_receipt(db_session):
    n = get_next_doc_number(db_session, "receipt", 2026, 5)
    assert n == "RCP-202605-0001"


def test_create_issuance_for_member(db_session):
    proj, tmpl, pm = _setup(db_session)
    issuance = create_issuance_for_member(
        db_session, project_id=proj.id, project_member_id=pm.id,
        recipient_organization=pm.organization_name,
        recipient_name=pm.representative_name,
        doc_type="invoice", fiscal_year=2026, month=5
    )
    assert issuance.id is not None
    assert issuance.status == "準備中"
    assert issuance.doc_number.startswith("INV-")
    assert len(issuance.lines) == 1
    assert int(issuance.lines[0].unit_price) == 10000


def test_mark_as_issued(db_session):
    proj, tmpl, pm = _setup(db_session)
    issuance = create_issuance_for_member(
        db_session, proj.id, pm.id,
        recipient_organization=pm.organization_name,
        recipient_name=pm.representative_name,
        doc_type="invoice", fiscal_year=2026, month=5
    )
    mark_as_issued(db_session, issuance.id, staff_id=None,
                   staff_name="田中", delivery_method="窓口手渡し")
    db_session.refresh(issuance)
    assert issuance.status == "発行済み"
    assert issuance.staff_name == "田中"


def test_record_payment(db_session):
    proj, tmpl, pm = _setup(db_session)
    issuance = create_issuance_for_member(
        db_session, proj.id, pm.id,
        recipient_organization=pm.organization_name,
        recipient_name=pm.representative_name,
        doc_type="invoice", fiscal_year=2026, month=5
    )
    mark_as_issued(db_session, issuance.id, None, "田中", "窓口手渡し")
    record_payment(db_session, issuance.id,
                   payment_date=date(2026, 5, 30),
                   amount=10000, payment_method="現金",
                   staff_name="田中")
    db_session.refresh(issuance)
    assert issuance.status == "支払済み"


def test_get_pending_for_project_member(db_session):
    proj, tmpl, pm = _setup(db_session)
    create_issuance_for_member(
        db_session, proj.id, pm.id,
        recipient_organization=pm.organization_name,
        recipient_name=pm.representative_name,
        doc_type="invoice", fiscal_year=2026, month=5
    )
    pending = get_pending_issuances_for_project_member(db_session, pm.id)
    assert len(pending) == 1
    assert pending[0].status == "準備中"


def test_create_counter_issuance(db_session):
    cat = create_category(db_session, "検定")
    tmpl = create_item_template(db_session, cat.id, "珠算検定受験料",
                                3000, "人", 0, "receipt", "珠算検定受験料として")
    proj = create_project(db_session, "珠算検定", cat.id, 2026, "counter")
    add_template_to_project(db_session, proj.id, tmpl.id)
    issuance = create_counter_issuance(
        db_session, project_id=proj.id,
        recipient_organization="△△そろばん教室",
        recipient_name="",
        doc_type="receipt", quantity=3,
        fiscal_year=2026, month=5
    )
    assert issuance.id is not None
    assert issuance.status == "発行済み"
    assert int(issuance.lines[0].quantity) == 3
    assert int(issuance.amount) == 9000
