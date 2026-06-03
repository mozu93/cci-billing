# tests/test_report_header.py
"""Task 9: レポート・再発行のヘッダが「名簿名」でなく「件名」であることを検証する。"""


def test_report_widgets_use_kenmei_header(qtbot, memory_db):
    from app.ui.report_tab import (
        UnpaidReportWidget, PaymentReportWidget, ProjectSummaryWidget)
    for cls in (UnpaidReportWidget, PaymentReportWidget, ProjectSummaryWidget):
        w = cls()
        qtbot.addWidget(w)
        assert "件名" in w.HEADERS
        assert "名簿名" not in w.HEADERS


def test_reissue_tab_uses_kenmei_header(qtbot, memory_db):
    from app.ui.reissue_tab import ReissueWidget
    w = ReissueWidget()
    qtbot.addWidget(w)
    headers = [w._table.horizontalHeaderItem(i).text()
               for i in range(w._table.columnCount())]
    assert "件名" in headers
    assert "名簿名" not in headers
