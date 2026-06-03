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


def _seed_duplicate_named_templates():
    """同名「視察研修会参加費」を別業務で2件登録し、(t1, t2) を返す。"""
    from app.database.connection import get_session
    from app.services.category_service import create_category
    from app.services.item_template_service import create_item_template
    s = get_session()
    c1 = create_category(s, "不動産部会")
    c2 = create_category(s, "建設部会")
    t1 = create_item_template(s, c1.id, "視察研修会参加費", 5000, "人", 0, "receipt", "")
    t2 = create_item_template(s, c2.id, "視察研修会参加費", 6000, "人", 0, "receipt", "")
    ids = (t1.id, t2.id)
    s.close()
    return ids


def test_freeissue_item_combo_shows_category_when_unfiltered(qtbot, memory_db):
    """業務名未選択時は、同名項目に業務名を併記して見分けられる。"""
    _seed_duplicate_named_templates()
    from app.ui.issuance_counter import IssuanceCounterWidget
    w = IssuanceCounterWidget()
    qtbot.addWidget(w)
    w._reload_master()
    row = w._rows[0]
    labels = [row.tmpl_combo.itemText(i) for i in range(row.tmpl_combo.count())]
    assert any("視察研修会参加費（不動産部会）" in t for t in labels)
    assert any("視察研修会参加費（建設部会）" in t for t in labels)


def test_freeissue_groups_by_item_category(qtbot, memory_db):
    """業務名を選ばず項目だけ選んでも、項目の業務名に集計される。"""
    _t1_id, t2_id = _seed_duplicate_named_templates()
    from app.ui.issuance_counter import IssuanceCounterWidget
    w = IssuanceCounterWidget()
    qtbot.addWidget(w)
    w._reload_master()
    row = w._rows[0]
    idx = next(i for i in range(row.tmpl_combo.count())
               if row.tmpl_combo.itemData(i) == t2_id)
    row.tmpl_combo.setCurrentIndex(idx)
    # 業務名コンボは未選択（None）のまま
    assert row.cat_combo.currentData() is None
    assert w._derive_project_name() == "建設部会"
