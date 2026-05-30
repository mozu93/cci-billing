# app/services/staff_service.py
from sqlalchemy.orm import Session
from app.database.models import Staff


def create_staff(session: Session, name: str) -> Staff:
    staff = Staff(name=name)
    session.add(staff)
    session.commit()
    session.refresh(staff)
    return staff


def get_active_staff(session: Session) -> list[Staff]:
    return session.query(Staff).filter_by(is_active=True).order_by(Staff.name).all()


def get_all_staff(session: Session) -> list[Staff]:
    return session.query(Staff).order_by(Staff.name).all()


def deactivate_staff(session: Session, staff_id: int) -> None:
    staff = session.get(Staff, staff_id)
    if staff:
        staff.is_active = False
        session.commit()


def reactivate_staff(session: Session, staff_id: int) -> None:
    staff = session.get(Staff, staff_id)
    if staff:
        staff.is_active = True
        session.commit()


def update_staff_name(session: Session, staff_id: int, name: str) -> Staff:
    staff = session.get(Staff, staff_id)
    staff.name = name
    session.commit()
    return staff
