# app/ui/counter_issuance_tab.py
from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from app.ui.issuance_counter import IssuanceCounterWidget
from app.ui.issuance_cross_member import IssuanceCrossMemberWidget


class CounterIssuanceTab(QWidget):
    """窓口発行：請求書発行タブと領収書発行タブに分割。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        inner = QTabWidget()

        inner.addTab(IssuanceCounterWidget("invoice"), "請求書発行")

        receipt_tab = QWidget()
        receipt_layout = QVBoxLayout(receipt_tab)
        receipt_layout.setContentsMargins(0, 0, 0, 0)
        receipt_inner = QTabWidget()
        receipt_inner.addTab(IssuanceCounterWidget("receipt"), "フリー発行")
        receipt_inner.addTab(IssuanceCrossMemberWidget(), "登録済発行")
        receipt_layout.addWidget(receipt_inner)
        inner.addTab(receipt_tab, "領収書発行")

        layout.addWidget(inner)
