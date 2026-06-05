"""Tests for IssuanceFromProjectWidget (TDD)."""
from PyQt6.QtWidgets import QPushButton, QComboBox, QLabel


def _texts(w):
    return [b.text() for b in w.findChildren(QPushButton)]


def test_widget_uses_kenmei_label(qtbot, memory_db):
    """発行元の選択ラベルが用語統一で「件名：」になっている。"""
    from app.ui.issuance_from_project import IssuanceFromProjectWidget
    w = IssuanceFromProjectWidget()
    qtbot.addWidget(w)
    labels = [lb.text() for lb in w.findChildren(QLabel)]
    assert "件名：" in labels
    assert "名簿：" not in labels


def test_widget_has_issue_and_batch_buttons(qtbot, memory_db):
    from app.ui.issuance_from_project import IssuanceFromProjectWidget
    w = IssuanceFromProjectWidget()
    qtbot.addWidget(w)
    texts = _texts(w)
    # 初期は請求書。種別が文言に含まれる
    assert "選択行に請求書を発行" in texts
    assert "全員に請求書を発行" in texts
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


def test_issue_button_labels_follow_doctype(qtbot, memory_db):
    from app.ui.issuance_from_project import IssuanceFromProjectWidget
    w = IssuanceFromProjectWidget()
    qtbot.addWidget(w)
    idx_inv = next(i for i in range(w._doctype_combo.count())
                   if w._doctype_combo.itemData(i) == "invoice")
    w._doctype_combo.setCurrentIndex(idx_inv)
    assert w._btn_issue.text() == "選択行に請求書を発行"
    assert w._btn_issue_all.text() == "全員に請求書を発行"
    idx_rcp = next(i for i in range(w._doctype_combo.count())
                   if w._doctype_combo.itemData(i) == "receipt")
    w._doctype_combo.setCurrentIndex(idx_rcp)
    assert w._btn_issue.text() == "選択行に領収書を発行"
    assert w._btn_issue_all.text() == "全員に領収書を発行"
