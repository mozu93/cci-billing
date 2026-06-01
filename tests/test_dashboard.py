# tests/test_dashboard.py


def test_dashboard_has_no_draft_section(qtbot, memory_db):
    from app.ui.dashboard import DashboardWidget
    w = DashboardWidget()
    qtbot.addWidget(w)
    assert not hasattr(w, "_draft_table")
