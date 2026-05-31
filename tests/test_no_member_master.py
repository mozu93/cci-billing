# tests/test_no_member_master.py
"""会員マスタ撤去ガードテスト"""


def test_member_master_removed():
    import importlib
    for mod in ("app.services.member_service", "app.ui.member_list",
                "app.ui.member_form"):
        try:
            importlib.import_module(mod)
            assert False, f"{mod} はまだ存在します"
        except ModuleNotFoundError:
            pass


def test_models_have_no_member_classes():
    import app.database.models as m
    assert not hasattr(m, "Member")
    assert not hasattr(m, "MemberNameHistory")


def test_settings_tab_has_no_member_master(qtbot, memory_db):
    from PyQt6.QtWidgets import QTabWidget
    from app.ui.settings_tab import SettingsTab
    w = SettingsTab()
    qtbot.addWidget(w)
    inner = w.findChild(QTabWidget)
    titles = [inner.tabText(i) for i in range(inner.count())]
    assert "会員マスタ" not in titles
