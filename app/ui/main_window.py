# app/ui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QTabWidget
from PyQt6.QtCore import pyqtSignal


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("商工会議所請求書・領収書発行システム")
        self.resize(780, 800)
        self._build_tabs()

    def _build_tabs(self):
        tabs = QTabWidget()

        from app.ui.counter_issuance_tab import CounterIssuanceTab
        tabs.addTab(CounterIssuanceTab(), "単発発行")

        from app.ui.batch_issuance_tab import BatchIssuanceTab
        tabs.addTab(BatchIssuanceTab(), "まとめて発行")

        from app.ui.reissue_tab import ReissueWidget
        tabs.addTab(ReissueWidget(), "修正・再発行")

        from app.ui.settings_tab import SettingsTab
        tabs.addTab(SettingsTab(), "設定")

        tabs.setCurrentIndex(0)
        self.setCentralWidget(tabs)
