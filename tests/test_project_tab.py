# tests/test_project_tab.py
from PyQt6.QtWidgets import QPushButton


def _texts(w):
    return [b.text() for b in w.findChildren(QPushButton)]


def test_project_tab_buttons_simplified(qtbot, memory_db):
    from app.ui.project_tab import ProjectTab
    w = ProjectTab()
    qtbot.addWidget(w)
    texts = _texts(w)
    assert "完了" in texts
    assert "受付開始（active）" not in texts
    assert "一括PDF生成" not in texts
    assert "アーカイブ" not in texts
