# app/services/member_service.py
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database.models import Member, MemberNameHistory


def create_member(session: Session, member_number: str | None = None,
                  organization_name: str = "", organization_kana: str = "",
                  representative_name: str = "", representative_kana: str = "",
                  postal_code: str = "", address: str = "",
                  phone: str = "", email: str = "",
                  is_member: bool = True, notes: str = "") -> Member:
    m = Member(
        member_number=member_number or None,
        organization_name=organization_name,
        organization_kana=organization_kana,
        representative_name=representative_name,
        representative_kana=representative_kana,
        postal_code=postal_code, address=address,
        phone=phone, email=email,
        is_member=is_member, notes=notes
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def get_member_by_id(session: Session, member_id: int) -> Member | None:
    return session.get(Member, member_id)


def search_members(session: Session, query: str,
                   active_only: bool = True) -> list[Member]:
    q = session.query(Member)
    if active_only:
        q = q.filter(Member.is_active.is_(True))
    if query:
        like = f"%{query}%"
        q = q.filter(or_(
            Member.member_number.ilike(f"{query}%"),
            Member.organization_name.ilike(like),
            Member.organization_kana.ilike(f"{query}%"),
            Member.representative_name.ilike(like),
            Member.representative_kana.ilike(f"{query}%"),
        ))
    return q.order_by(Member.organization_kana, Member.organization_name).all()


def update_member_name(session: Session, member_id: int,
                       new_organization_name: str | None = None,
                       new_organization_kana: str | None = None,
                       new_representative_name: str | None = None,
                       new_representative_kana: str | None = None,
                       reason: str = "") -> Member:
    m = session.get(Member, member_id)
    history = MemberNameHistory(
        member_id=m.id,
        organization_name=m.organization_name,
        representative_name=m.representative_name,
        changed_at=datetime.now(),
        reason=reason
    )
    session.add(history)
    if new_organization_name is not None:
        m.organization_name = new_organization_name
    if new_organization_kana is not None:
        m.organization_kana = new_organization_kana
    if new_representative_name is not None:
        m.representative_name = new_representative_name
    if new_representative_kana is not None:
        m.representative_kana = new_representative_kana
    session.commit()
    session.refresh(m)
    return m


def deactivate_member(session: Session, member_id: int) -> None:
    m = session.get(Member, member_id)
    if m:
        m.is_active = False
        session.commit()


def get_recipient_label(member: Member) -> str:
    if member.organization_name and member.representative_name:
        return f"{member.organization_name} {member.representative_name} 様"
    elif member.organization_name:
        return f"{member.organization_name} 御中"
    else:
        return f"{member.representative_name} 様"
