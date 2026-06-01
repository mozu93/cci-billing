# tests/test_counter_issuance_tab.py
from PyQt6.QtWidgets import QTabWidget


def _tab_titles(tabwidget: QTabWidget) -> list[str]:
    return [tabwidget.tabText(i) for i in range(tabwidget.count())]


def test_counter_issuance_subtabs(qtbot, memory_db):
    from app.ui.counter_issuance_tab import CounterIssuanceTab
    w = CounterIssuanceTab()
    qtbot.addWidget(w)
    inner = w.findChild(QTabWidget)
    assert inner is not None
    assert _tab_titles(inner) == ["フリー発行", "登録済発行"]
