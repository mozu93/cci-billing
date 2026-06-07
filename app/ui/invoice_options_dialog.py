# app/ui/invoice_options_dialog.py
import calendar
from datetime import date
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QDateEdit, QPushButton, QLabel
)
from PyQt6.QtCore import QDate


def _next_month_end(from_date=None) -> date:
    """指定日（省略時は今日）の翌月末を返す。"""
    d = from_date or date.today()
    if hasattr(d, "date"):
        d = d.date()
    y, m = (d.year, d.month + 1) if d.month < 12 else (d.year + 1, 1)
    return date(y, m, calendar.monthrange(y, m)[1])


class InvoiceOptionsDialog(QDialog):
    """請求書PDF生成前に支払期限を確認・変更するダイアログ。"""

    def __init__(self, issued_at=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("支払期限の確認")
        self.setFixedSize(300, 130)

        default = _next_month_end(issued_at)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("支払期限を確認・変更してください。"))

        form = QFormLayout()
        self._due = QDateEdit(QDate(default.year, default.month, default.day))
        self._due.setCalendarPopup(True)
        self._due.setDisplayFormat("yyyy/MM/dd")
        form.addRow("支払期限", self._due)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("発行")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def due_date(self) -> date:
        qd = self._due.date()
        return date(qd.year(), qd.month(), qd.day())
