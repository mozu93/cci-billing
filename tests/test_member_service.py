# tests/test_member_service.py
from app.services.member_service import (
    create_member, search_members, update_member_name, get_member_by_id
)


def test_create_member(db_session):
    m = create_member(db_session, member_number="A-001",
                      organization_name="○○商事", organization_kana="マルマルショウジ",
                      representative_name="田中 太郎", representative_kana="タナカ タロウ")
    assert m.id is not None
    assert m.member_number == "A-001"


def test_search_by_organization_name(db_session):
    create_member(db_session, member_number="A-001", organization_name="○○商事",
                  organization_kana="マルマルショウジ")
    create_member(db_session, member_number="A-002", organization_name="△△産業",
                  organization_kana="サンカクサンカクサンギョウ")
    result = search_members(db_session, "商事")
    assert len(result) == 1
    assert result[0].organization_name == "○○商事"


def test_search_by_member_number(db_session):
    create_member(db_session, member_number="A-001", organization_name="○○商事",
                  organization_kana="マルマルショウジ")
    result = search_members(db_session, "A-001")
    assert len(result) == 1


def test_search_by_kana(db_session):
    create_member(db_session, member_number="A-001", organization_name="○○商事",
                  organization_kana="マルマルショウジ")
    result = search_members(db_session, "マルマル")
    assert len(result) == 1


def test_update_name_creates_history(db_session):
    m = create_member(db_session, member_number="A-001",
                      organization_name="旧社名", organization_kana="キュウシャメイ")
    update_member_name(db_session, m.id, new_organization_name="新社名",
                       new_organization_kana="シンシャメイ", reason="商号変更")
    updated = get_member_by_id(db_session, m.id)
    assert updated.organization_name == "新社名"
    assert len(updated.name_history) == 1
    assert updated.name_history[0].organization_name == "旧社名"
