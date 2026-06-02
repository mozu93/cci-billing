"""Tests for IssuanceFromProjectWidget (TDD)."""
from PyQt6.QtWidgets import QPushButton, QComboBox


def _texts(w):
    return [b.text() for b in w.findChildren(QPushButton)]


def test_widget_has_issue_and_batch_buttons(qtbot, memory_db):
    from app.ui.issuance_from_project import IssuanceFromProjectWidget
    w = IssuanceFromProjectWidget()
    qtbot.addWidget(w)
    texts = _texts(w)
    assert "選択した行を発行" in texts
    assert "全員まとめて発行" in texts
    # 旧2段階ボタンが無い
    assert "準備（採番）" not in texts


def test_widget_has_doctype_combo(qtbot, memory_db):
    from app.ui.issuance_from_project import IssuanceFromProjectWidget
    from PyQt6.QtCore import Qt
    w = IssuanceFromProjectWidget()
    qtbot.addWidget(w)
    combos = w.findChildren(QComboBox)
    # いずれかのコンボに invoice/receipt のデータが入っている
    found = False
    for c in combos:
        datas = [c.itemData(i) for i in range(c.count())]
        if "invoice" in datas and "receipt" in datas:
            found = True
    assert found
