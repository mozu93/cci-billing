# app/ui/settings_tab.py
from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        inner = QTabWidget()

        from app.ui.company_settings import CompanySettingsWidget
        from app.ui.staff_management import StaffManagementWidget
        from app.ui.category_management import CategoryManagementWidget
        from app.ui.item_template_management import ItemTemplateManagementWidget
        from app.ui.member_list import MemberListWidget

        inner.addTab(CompanySettingsWidget(), "発行元情報")
        inner.addTab(StaffManagementWidget(), "スタッフ管理")
        inner.addTab(CategoryManagementWidget(), "カテゴリ")
        inner.addTab(ItemTemplateManagementWidget(), "請求項目テンプレート")
        inner.addTab(MemberListWidget(), "会員マスタ")
        layout.addWidget(inner)
