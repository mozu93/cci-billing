# app/ui/issuance_tab.py
from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from app.ui.issuance_from_project import IssuanceFromProjectWidget
from app.ui.issuance_cross_member import IssuanceCrossMemberWidget
from app.ui.issuance_counter import IssuanceCounterWidget
from app.ui.payment_dialog import PaymentManagementWidget


class IssuanceTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        inner = QTabWidget()
        inner.addTab(IssuanceFromProjectWidget(), "事業から発行")
        inner.addTab(IssuanceCrossMemberWidget(), "人を検索して発行")
        inner.addTab(IssuanceCounterWidget(), "窓口型（即時発行）")
        inner.addTab(PaymentManagementWidget(), "支払管理")
        layout.addWidget(inner)
