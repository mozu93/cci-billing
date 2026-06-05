# tests/test_batch_pdf.py
"""TDDテスト: generate_batch_pdf の doc_type 引数と発行済み更新を検証する"""
import os
from app.services.category_service import create_category
from app.services.item_template_service import create_item_template
from app.services.project_service import (
    create_project, add_template_to_project, add_roster_entries,
    get_project_members,
)
from app.database.models import CompanySettings, Issuance
from app.services.issuance_service import (
    create_issuance_for_member, mark_as_issued, get_project_issuances,
)


def _setup_receipt_project(db_session):
    """領収書テンプレートを持つプロジェクトと名簿を組み立てる"""
    cat = create_category(db_session, "青年部")
    tmpl = create_item_template(
        db_session, cat.id, "青年部会費", 10000, "式", 0, "receipt", ""
    )
    proj = create_project(db_session, "2026年度 青年部会費", cat.id, 2026, "list")
    add_template_to_project(db_session, proj.id, tmpl.id)
    add_roster_entries(db_session, proj.id, [
        {"organization_name": "○○商事株式会社",
         "representative_name": "田中 太郎"},
        {"organization_name": "△△産業",
         "representative_name": "鈴木 次郎"},
    ])
    return proj


def _make_company():
    return CompanySettings(
        name="○○商工会議所",
        postal_code="123-4567",
        address="東京都千代田区1-1-1",
        phone="03-1234-5678",
        invoice_reg_number="T1234567890123",
    )


def test_batch_pdf_receipt_generates_files(db_session, tmp_path):
    """doc_type="receipt" を渡すと領収書PDFが生成される"""
    from app.services.pdf.batch_pdf import generate_batch_pdf
    proj = _setup_receipt_project(db_session)
    company = _make_company()

    paths = generate_batch_pdf(
        db_session, proj.id, company, str(tmp_path),
        doc_type="receipt"
    )

    assert len(paths) == 2
    for p in paths:
        assert os.path.exists(p), f"PDF not found: {p}"
        assert os.path.getsize(p) > 1000, f"PDF too small: {p}"


def test_batch_pdf_marks_issuances_as_issued(db_session, tmp_path):
    """generate_batch_pdf 実行後、対象issuanceのstatusが"発行済み"になる"""
    from app.services.pdf.batch_pdf import generate_batch_pdf
    proj = _setup_receipt_project(db_session)
    company = _make_company()

    generate_batch_pdf(
        db_session, proj.id, company, str(tmp_path),
        doc_type="receipt"
    )

    issuances = get_project_issuances(db_session, proj.id)
    assert len(issuances) == 2
    for iss in issuances:
        assert iss.status == "発行済み", (
            f"Expected '発行済み' but got '{iss.status}' for {iss.doc_number}"
        )


def test_batch_pdf_invoice_generates_files(db_session, tmp_path):
    """doc_type="invoice" (デフォルト) で請求書PDFが生成される"""
    from app.services.pdf.batch_pdf import generate_batch_pdf
    cat = create_category(db_session, "事業部")
    tmpl = create_item_template(
        db_session, cat.id, "事業参加費", 5000, "式", 0, "invoice", ""
    )
    proj = create_project(db_session, "2026年度 事業参加費", cat.id, 2026, "list")
    add_template_to_project(db_session, proj.id, tmpl.id)
    add_roster_entries(db_session, proj.id, [
        {"organization_name": "○○商事", "representative_name": "田中"},
    ])
    company = _make_company()

    paths = generate_batch_pdf(
        db_session, proj.id, company, str(tmp_path),
        doc_type="invoice"
    )

    assert len(paths) == 1
    assert os.path.exists(paths[0])


def test_batch_pdf_invoice_not_reuse_existing_receipt(db_session, tmp_path):
    """既存の領収書がある会員に対して doc_type="invoice" を指定すると、
    領収書を流用せず新規に請求書 issuance が作成される（doc_type フィルタ不具合の再現）。"""
    from app.services.pdf.batch_pdf import generate_batch_pdf

    # --- セットアップ: 請求書テンプレートを持つプロジェクトに会員1名 ---
    cat = create_category(db_session, "本部")
    tmpl = create_item_template(
        db_session, cat.id, "年会費", 8000, "式", 0, "invoice", ""
    )
    proj = create_project(db_session, "2026年度 年会費", cat.id, 2026, "list")
    add_template_to_project(db_session, proj.id, tmpl.id)
    add_roster_entries(db_session, proj.id, [
        {"organization_name": "○○工業株式会社", "representative_name": "山田 花子"},
    ])
    pm = get_project_members(db_session, proj.id)[0]

    # --- 前提条件: この会員にすでに領収書 issuance が存在する ---
    receipt_iss = create_issuance_for_member(
        db_session, proj.id, pm.id,
        recipient_organization=pm.organization_name,
        recipient_name=pm.representative_name,
        doc_type="receipt", fiscal_year=2026, month=4,
    )
    mark_as_issued(db_session, receipt_iss.id, staff_id=None, staff_name="")

    # --- バグ再現: doc_type="invoice" で一括生成 ---
    company = _make_company()
    generate_batch_pdf(
        db_session, proj.id, company, str(tmp_path),
        doc_type="invoice"
    )

    # --- アサーション: 請求書 issuance が新規作成されていること ---
    invoice_count = (
        db_session.query(Issuance)
        .filter_by(project_member_id=pm.id, doc_type="invoice")
        .count()
    )
    assert invoice_count == 1, (
        f"Expected 1 invoice issuance, got {invoice_count}. "
        "The receipt may have been reused due to missing doc_type filter."
    )
