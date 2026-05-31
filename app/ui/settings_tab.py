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
        from app.ui.email_settings import EmailSettingsWidget
        from app.ui.backup_settings import BackupSettingsWidget

        inner.addTab(CompanySettingsWidget(), "発行元情報")
        inner.addTab(StaffManagementWidget(), "スタッフ管理")
        inner.addTab(CategoryManagementWidget(), "業務名")
        inner.addTab(ItemTemplateManagementWidget(), "請求項目テンプレート")
        inner.addTab(EmailSettingsWidget(), "メール設定")
        inner.addTab(BackupSettingsWidget(), "バックアップ")
        layout.addWidget(inner)
