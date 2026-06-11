# app/services/member_service.py
import csv
import io
from sqlalchemy.orm import Session
from app.database.models import Member

_COLUMN_ALIASES = {
    "member_number":       ["会員番号", "会員no", "会員ｎｏ", "memberid", "member_id"],
    "organization_name":   ["事業所名", "会社名", "法人名", "organization"],
    "organization_kana":   ["フリガナ", "事業所フリガナ", "フリガナ（事業所）", "kana"],
    "representative_name": ["氏名", "代表者名", "担当者名", "name"],
    "representative_kana": ["氏名フリガナ", "代表者フリガナ", "氏名かな"],
    "phone":               ["電話番号", "tel", "電話", "phone"],
    "email":               ["メール", "メールアドレス", "mail", "e-mail"],
    "postal_code":         ["郵便番号", "zip", "zipcode"],
    "address":             ["住所", "住所1", "住所１", "address1"],
    "address2":            ["住所2", "住所２", "建物名", "番地以下"],
}

_MEMBER_FIELDS = set(_COLUMN_ALIASES.keys())

# 小文字マップ: lowercase alias → field name
_LOWER_MAP: dict[str, str] = {}
for _field, _aliases in _COLUMN_ALIASES.items():
    _LOWER_MAP[_field.lower()] = _field
    for _a in _aliases:
        _LOWER_MAP[_a.lower()] = _field


def import_from_csv(session: Session, file_path: str) -> int:
    """CSVから会員マスタを一括登録。既存データ全削除→再登録。戻り値：登録件数。"""
    raw = open(file_path, "rb").read()
    text = ""
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return 0

    # ヘッダー → 内部フィールド名マップ
    col_map: dict[str, str] = {}
    for hdr in reader.fieldnames:
        field = _LOWER_MAP.get(hdr.strip().lower())
        if field:
            col_map[hdr] = field

    session.query(Member).delete()
    session.flush()

    count = 0
    for row in reader:
        data: dict[str, str] = {}
        for hdr, field in col_map.items():
            data[field] = (row.get(hdr) or "").strip()
        if not data.get("organization_name") and not data.get("member_number"):
            continue
        kwargs = {k: v for k, v in data.items() if k in _MEMBER_FIELDS}
        session.add(Member(**kwargs))
        count += 1

    session.commit()
    return count


def get_all_members(session: Session) -> list:
    return session.query(Member).order_by(Member.organization_name).all()


def search_members(session: Session, query: str, limit: int = 50) -> list:
    q = (query or "").strip()
    if not q:
        return []
    from sqlalchemy import or_
    return (session.query(Member)
            .filter(or_(
                Member.organization_name.contains(q),
                Member.organization_kana.contains(q),
                Member.member_number.contains(q),
            ))
            .limit(limit)
            .all())


def count_members(session: Session) -> int:
    return session.query(Member).count()
