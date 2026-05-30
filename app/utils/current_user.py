# app/utils/current_user.py
_staff_id: int | None = None
_staff_name: str = ""


def set_current(staff_id: int, staff_name: str) -> None:
    global _staff_id, _staff_name
    _staff_id = staff_id
    _staff_name = staff_name


def get_id() -> int | None:
    return _staff_id


def get_name() -> str:
    return _staff_name


def clear() -> None:
    global _staff_id, _staff_name
    _staff_id = None
    _staff_name = ""


def is_logged_in() -> bool:
    return _staff_id is not None
