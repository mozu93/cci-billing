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


def _seed_two_members_with_issuances():
    """○○商事=請求書のみ発行済み / △△工業=請求書も領収書も発行済み。proj_id を返す。"""
    from app.database.connection import get_session
    from app.services.category_service import create_category
    from app.services.item_template_service import create_item_template
    from app.services.project_service import (
        create_project, add_template_to_project, add_roster_entries,
        get_project_members,
    )
    from app.services.issuance_service import create_issuance_for_member, mark_as_issued
    s = get_session()
    cat = create_category(s, "青年部")
    tmpl = create_item_template(s, cat.id, "会費", 5000, "式", 0, "invoice", "")
    proj = create_project(s, "2026 青年部会費", cat.id, 2026, "list")
    add_template_to_project(s, proj.id, tmpl.id)
    add_roster_entries(s, proj.id, [
        {"organization_name": "○○商事"},
        {"organization_name": "△△工業"},
    ])
    pms = get_project_members(s, proj.id)
    inv1 = create_issuance_for_member(s, proj.id, pms[0].id, "○○商事", "",
                                      "invoice", 2026, 5)
    mark_as_issued(s, inv1.id, None, "田中", "窓口手渡し")
    inv2 = create_issuance_for_member(s, proj.id, pms[1].id, "△△工業", "",
                                      "invoice", 2026, 5)
    mark_as_issued(s, inv2.id, None, "田中", "窓口手渡し")
    rcp2 = create_issuance_for_member(s, proj.id, pms[1].id, "△△工業", "",
                                      "receipt", 2026, 5)
    mark_as_issued(s, rcp2.id, None, "田中", "窓口手渡し")
    proj_id = proj.id
    s.close()
    return proj_id


def _select_project(w, proj_id):
    for i in range(w._proj_combo.count()):
        if w._proj_combo.itemData(i) == proj_id:
            w._proj_combo.setCurrentIndex(i)
            return


def test_two_columns_show_invoice_and_receipt_status(qtbot, memory_db):
    from app.ui.issuance_from_project import (
        IssuanceFromProjectWidget, COL_ORG, COL_INV, COL_RCP,
    )
    proj_id = _seed_two_members_with_issuances()
    w = IssuanceFromProjectWidget()
    qtbot.addWidget(w)
    _select_project(w, proj_id)
    w._filter_combo.setCurrentIndex(1)  # すべて
    w._load_members()

    assert w._table.rowCount() == 2
    rows = {}
    for r in range(w._table.rowCount()):
        org = w._table.item(r, COL_ORG).text()
        rows[org] = (w._table.item(r, COL_INV).text(),
                     w._table.item(r, COL_RCP).text())
    # ○○商事：請求書発行済み・領収書未発行
    assert "発行済" in rows["○○商事"][0]
    assert "INV-" in rows["○○商事"][0]
    assert rows["○○商事"][1] == "未発行"
    # △△工業：請求書・領収書とも発行済み（古い方が消えない）
    assert "発行済" in rows["△△工業"][0]
    assert "INV-" in rows["△△工業"][0]
    assert "発行済" in rows["△△工業"][1]
    assert "RCP-" in rows["△△工業"][1]


def test_unissued_filter_is_per_doctype(qtbot, memory_db):
    from app.ui.issuance_from_project import IssuanceFromProjectWidget
    proj_id = _seed_two_members_with_issuances()
    # ○○商事=請求書発行済み/領収書未発行、△△工業=両方発行済み
    w = IssuanceFromProjectWidget()
    qtbot.addWidget(w)
    _select_project(w, proj_id)

    # 書類種別=請求書、未発行のみ → 両者とも請求書発行済みなので0件
    idx_inv = next(i for i in range(w._doctype_combo.count())
                   if w._doctype_combo.itemData(i) == "invoice")
    w._filter_combo.setCurrentIndex(0)  # 未発行のみ
    w._doctype_combo.setCurrentIndex(idx_inv)
    w._load_members()
    assert w._table.rowCount() == 0

    # 書類種別=領収書に切替 → 切替だけで再読込され、領収書未発行の○○商事が出る
    idx_rcp = next(i for i in range(w._doctype_combo.count())
                   if w._doctype_combo.itemData(i) == "receipt")
    w._doctype_combo.setCurrentIndex(idx_rcp)  # currentIndexChanged で再読込
    orgs = [w._table.item(r, 1).text() for r in range(w._table.rowCount())]
    assert "○○商事" in orgs       # 領収書未発行
    assert "△△工業" not in orgs   # 領収書発行済み
