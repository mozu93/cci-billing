# app/ui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QLabel
from PyQt6.QtCore import pyqtSignal


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("商工会議所請求書・領収書発行システム")
        self.resize(1200, 800)
        self._build_tabs()

    def _build_tabs(self):
        tabs = QTabWidget()

        from app.ui.dashboard import DashboardWidget
        tabs.addTab(DashboardWidget(), "ダッシュボード")

        from app.ui.project_tab import ProjectTab
        tabs.addTab(ProjectTab(), "事業管理")

        from app.ui.issuance_tab import IssuanceTab
        tabs.addTab(IssuanceTab(), "発行")

        from app.ui.report_tab import ReportTab
        tabs.addTab(ReportTab(), "レポート")

        from app.ui.settings_tab import SettingsTab
        tabs.addTab(SettingsTab(), "設定")

        self.setCentralWidget(tabs)
