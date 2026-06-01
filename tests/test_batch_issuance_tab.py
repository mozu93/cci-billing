# tests/test_batch_issuance_tab.py
from PyQt6.QtWidgets import QTabWidget


def _tab_titles(tabwidget: QTabWidget) -> list[str]:
    return [tabwidget.tabText(i) for i in range(tabwidget.count())]


def test_batch_issuance_subtabs(qtbot, memory_db):
    from app.ui.batch_issuance_tab import BatchIssuanceTab
    w = BatchIssuanceTab()
    qtbot.addWidget(w)
    inner = w.findChild(QTabWidget)
    assert inner is not None
    assert _tab_titles(inner) == ["名簿登録", "登録名簿から発行", "入金管理"]
