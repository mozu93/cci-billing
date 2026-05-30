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
        tabs.addTab(QLabel("ダッシュボード（Plan 2で実装）"), "ダッシュボード")
        tabs.addTab(QLabel("事業管理（Plan 2で実装）"), "事業管理")
        tabs.addTab(QLabel("発行（Plan 2で実装）"), "発行")
        tabs.addTab(QLabel("レポート（Plan 4で実装）"), "レポート")

        from app.ui.settings_tab import SettingsTab
        tabs.addTab(SettingsTab(), "設定")

        self.setCentralWidget(tabs)
