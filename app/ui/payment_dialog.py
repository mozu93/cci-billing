# app/ui/payment_dialog.py
from datetime import date
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QDateEdit, QSpinBox, QComboBox, QLineEdit,
    QPushButton, QLabel, QWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from app.database.connection import get_session
from app.services.issuance_service import record_payment, get_project_issuances
from app.services.project_service import get_projects
from app.utils import current_user


class PaymentManagementWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load_projects()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("発行済み書類の支払管理"))

        top = QHBoxLayout()
        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(300)
        self._proj_combo.currentIndexChanged.connect(self._load)
        self._status_combo = QComboBox()
        self._status_combo.addItems(["発行済み", "支払済み", "すべて"])
        self._status_combo.currentIndexChanged.connect(self._load)
        top.addWidget(QLabel("名簿："))
        top.addWidget(self._proj_combo)
        top.addWidget(QLabel("状態："))
        top.addWidget(self._status_combo)
        top.addStretch()
        layout.addLayout(top)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["発行番号", "宛先", "金額", "状態", "発行日"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_pay = QPushButton("支払済みに更新")
        btn_pay.clicked.connect(self._mark_paid)
        btn_row.addWidget(btn_pay)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _load_projects(self):
        session = get_session()
        try:
            projects = get_projects(session, status="active")
        finally:
            session.close()
        self._proj_combo.clear()
        for p in projects:
            self._proj_combo.addItem(p.name, p.id)
        self._load()

    def _load(self):
        project_id = self._proj_combo.currentData()
        if project_id is None:
            return
        status_text = self._status_combo.currentText()
        status = None if status_text == "すべて" else status_text
        session = get_session()
        try:
            issuances = get_project_issuances(session, project_id, status)
        finally:
            session.close()
        self._table.setRowCount(0)
        for iss in issuances:
            row = self._table.rowCount()
            self._table.insertRow(row)
            recipient = iss.recipient_organization or iss.recipient_name
            issued = iss.issued_at.strftime("%Y/%m/%d") if iss.issued_at else ""
            for col, val in enumerate([
                iss.doc_number, recipient,
                f"¥{int(iss.amount):,}", iss.status, issued
            ]):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, iss.id)
                self._table.setItem(row, col, item)

    def _mark_paid(self):
        row = self._table.currentRow()
        if row < 0:
            return
        issuance_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        dlg = PaymentDialog(issuance_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()


class PaymentDialog(QDialog):
    def __init__(self, issuance_id: int, parent=None):
        super().__init__(parent)
        self._issuance_id = issuance_id
        self.setWindowTitle("入金記録")
        self.setFixedSize(360, 260)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._date = QDateEdit(QDate.currentDate())
        self._date.setCalendarPopup(True)
        self._amount = QSpinBox()
        self._amount.setRange(0, 99999999)
        session = get_session()
        try:
            from app.database.models import Issuance
            iss = session.get(Issuance, self._issuance_id)
            if iss:
                self._amount.setValue(int(iss.amount))
        finally:
            session.close()
        self._method = QComboBox()
        self._method.addItems(["現金", "振込", "その他"])
        self._notes = QLineEdit()
        form.addRow("入金日", self._date)
        form.addRow("入金額（円）", self._amount)
        form.addRow("入金方法", self._method)
        form.addRow("備考", self._notes)
        layout.addLayout(form)
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("記録して支払済みにする")
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _save(self):
        qd = self._date.date()
        payment_date = date(qd.year(), qd.month(), qd.day())
        session = get_session()
        try:
            record_payment(
                session,
                issuance_id=self._issuance_id,
                payment_date=payment_date,
                amount=self._amount.value(),
                payment_method=self._method.currentText(),
                staff_id=current_user.get_id(),
                staff_name=current_user.get_name(),
                notes=self._notes.text().strip()
            )
        finally:
            session.close()
        self.accept()
