# tests/test_dashboard.py


def test_dashboard_has_no_draft_section(qtbot, memory_db):
    from app.ui.dashboard import DashboardWidget
    w = DashboardWidget()
    qtbot.addWidget(w)
    assert not hasattr(w, "_draft_table")


def test_dashboard_table_column_headers(qtbot, memory_db):
    """ダッシュボードの列が請求書発行済・領収書発行済・未発行になっている。"""
    from app.ui.dashboard import DashboardWidget
    w = DashboardWidget()
    qtbot.addWidget(w)
    headers = [w._table.horizontalHeaderItem(i).text()
               for i in range(w._table.columnCount())]
    assert "請求書発行済" in headers
    assert "領収書発行済" in headers
    assert "未発行" in headers
    assert "発行済" not in headers
    assert "支払済" not in headers
