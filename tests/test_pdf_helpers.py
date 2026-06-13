# tests/test_pdf_helpers.py
from app.database.models import CompanySettings, BankAccount, SealImage, Project


def test_get_issuer_for_project_uses_project_company(db_session):
    from app.utils.pdf_helpers import get_issuer_for_project

    cs_default = CompanySettings(name="デフォルト会社", is_default=True)
    cs_other   = CompanySettings(name="別会社",         is_default=False)
    db_session.add_all([cs_default, cs_other])
    db_session.commit()

    bank = BankAccount(company_id=cs_other.id, label="口座A",
                       bank_name="○○銀行", is_default=True)
    db_session.add(bank)
    db_session.commit()

    proj = Project(name="PJ", fiscal_year=2026, project_type="list",
                   company_settings_id=cs_other.id, bank_account_id=bank.id)
    db_session.add(proj)
    db_session.commit()

    company, ba, seal = get_issuer_for_project(db_session, proj)
    assert company.id == cs_other.id
    assert ba.id == bank.id
    assert seal is None


def test_get_issuer_for_project_falls_back_to_default(db_session):
    from app.utils.pdf_helpers import get_issuer_for_project

    cs = CompanySettings(name="デフォルト会社", is_default=True)
    db_session.add(cs)
    db_session.commit()

    bank = BankAccount(company_id=cs.id, label="口座A",
                       bank_name="○○銀行", is_default=True)
    db_session.add(bank)
    db_session.commit()

    proj = Project(name="PJ", fiscal_year=2026, project_type="list")
    db_session.add(proj)
    db_session.commit()

    company, ba, seal = get_issuer_for_project(db_session, proj)
    assert company.id == cs.id
    assert ba.id == bank.id


def test_get_issuer_for_project_respects_print_seal_false(db_session):
    from app.utils.pdf_helpers import get_issuer_for_project

    cs = CompanySettings(name="会社", is_default=True, print_seal=False)
    db_session.add(cs)
    db_session.commit()

    seal_img = SealImage(company_id=cs.id, label="印鑑", path="/tmp/seal.png",
                         is_default=True)
    db_session.add(seal_img)
    db_session.commit()

    proj = Project(name="PJ", fiscal_year=2026, project_type="list",
                   seal_image_id=seal_img.id)
    db_session.add(proj)
    db_session.commit()

    _, _, seal = get_issuer_for_project(db_session, proj)
    assert seal is None  # print_seal=False なので常に None


def test_get_issuer_for_project_project_none_falls_back(db_session):
    from app.utils.pdf_helpers import get_issuer_for_project

    cs = CompanySettings(name="会社", is_default=True)
    db_session.add(cs)
    db_session.commit()

    company, _, _ = get_issuer_for_project(db_session, None)
    assert company.id == cs.id
