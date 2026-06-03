from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem


def _seed_category_and_template():
    from app.database.connection import get_session
    from app.services.category_service import create_category
    from app.services.item_template_service import create_item_template
    s = get_session()
    cat = create_category(s, "不動産部会")
    t = create_item_template(s, cat.id, "視察研修会参加費", 5000, "人", 0, "receipt", "")
    ids = (cat.id, t.id)
    s.close()
    return ids


def _select_category(dlg, cat_id):
    idx = next(i for i in range(dlg._category.count())
               if dlg._category.itemData(i) == cat_id)
    dlg._category.setCurrentIndex(idx)


def _add_template(dlg, tmpl_id):
    item = QListWidgetItem("x")
    item.setData(Qt.ItemDataRole.UserRole, tmpl_id)
    dlg._selected_list.addItem(item)


def test_project_form_saves_title_as_name(qtbot, memory_db):
    cat_id, t_id = _seed_category_and_template()
    from app.ui.project_form import ProjectFormDialog
    dlg = ProjectFormDialog()
    qtbot.addWidget(dlg)
    _select_category(dlg, cat_id)
    dlg._title.setText("2026 視察研修会参加費")
    _add_template(dlg, t_id)
    dlg._save()

    from app.database.connection import get_session
    from app.services.project_service import get_projects
    s = get_session()
    names = [p.name for p in get_projects(s)]
    s.close()
    assert "2026 視察研修会参加費" in names


def test_project_form_requires_title(qtbot, memory_db, monkeypatch):
    cat_id, t_id = _seed_category_and_template()
    import app.ui.project_form as pf
    monkeypatch.setattr(pf.QMessageBox, "warning", lambda *a, **k: None)
    dlg = pf.ProjectFormDialog()
    qtbot.addWidget(dlg)
    _select_category(dlg, cat_id)
    _add_template(dlg, t_id)
    # 件名は空のまま
    dlg._save()

    from app.database.connection import get_session
    from app.services.project_service import get_projects
    s = get_session()
    count = len(get_projects(s))
    s.close()
    assert count == 0  # 件名未入力なので作成されない
