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
    assert _tab_titles(inner) == ["請求・領収書データ", "登録データから発行", "入金管理"]


def test_batch_issuance_tab_titles_renamed(qtbot, memory_db):
    from PyQt6.QtWidgets import QTabWidget
    from app.ui.batch_issuance_tab import BatchIssuanceTab
    w = BatchIssuanceTab()
    qtbot.addWidget(w)
    inner = w.findChild(QTabWidget)
    titles = [inner.tabText(i) for i in range(inner.count())]
    assert "請求・領収書データ" in titles
    assert "登録データから発行" in titles
    assert "名簿登録" not in titles
