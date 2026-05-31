# tests/test_models.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database.models import Base


def test_create_all_tables():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = {row[0] for row in result}
    assert "staff" in tables
    assert "categories" in tables
    assert "item_templates" in tables
    assert "company_settings" in tables
    assert "projects" in tables
    assert "issuances" in tables
    session.close()
