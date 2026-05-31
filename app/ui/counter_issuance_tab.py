# app/ui/counter_issuance_tab.py
from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from app.ui.issuance_counter import IssuanceCounterWidget
from app.ui.issuance_cross_member import IssuanceCrossMemberWidget


class CounterIssuanceTab(QWidget):
    """窓口発行：その場で1件ずつ発行する作業をまとめるタブ。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        inner = QTabWidget()
        inner.addTab(IssuanceCounterWidget(), "フリー発行")
        inner.addTab(IssuanceCrossMemberWidget(), "随時受取")
        layout.addWidget(inner)
