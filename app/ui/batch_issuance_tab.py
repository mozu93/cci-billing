# app/ui/batch_issuance_tab.py
from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from app.ui.project_tab import ProjectTab
from app.ui.issuance_from_project import IssuanceFromProjectWidget
from app.ui.payment_dialog import PaymentManagementWidget


class BatchIssuanceTab(QWidget):
    """まとめて発行：名簿単位の準備・一括発行・入金管理をまとめるタブ。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        inner = QTabWidget()
        inner.addTab(ProjectTab(), "請求・領収書データ")
        inner.addTab(IssuanceFromProjectWidget("invoice"), "請求書発行")
        inner.addTab(IssuanceFromProjectWidget("receipt"), "領収書発行")
        inner.addTab(PaymentManagementWidget(), "入金管理")
        layout.addWidget(inner)
