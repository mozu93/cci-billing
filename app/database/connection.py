# app/database/connection.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.utils.app_config import get_db_url

_SessionFactory = None


def get_engine(url: str | None = None):
    return create_engine(url or get_db_url(), echo=False)


def _migrate(engine):
    """既存DBに不足カラムを追加するマイグレーション"""
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(company_settings)"))}
        if "print_seal" not in cols:
            conn.execute(text(
                "ALTER TABLE company_settings ADD COLUMN print_seal BOOLEAN DEFAULT 1"))
            conn.commit()

        pm_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(project_members)"))}
        if "department" not in pm_cols:
            conn.execute(text(
                "ALTER TABLE project_members ADD COLUMN department VARCHAR(100) DEFAULT ''"))
            conn.commit()


def init_db(url: str | None = None):
    global _SessionFactory
    from app.database.models import Base
    engine = get_engine(url)
    Base.metadata.create_all(engine)
    _migrate(engine)
    _SessionFactory = sessionmaker(bind=engine)


def get_session() -> Session:
    if _SessionFactory is None:
        init_db()
    return _SessionFactory()
