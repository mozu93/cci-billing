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


_PAY_COLS = [
    ("発行番号", 120),
    ("会員番号",  90),
    ("宛先",     200),
    ("フリガナ", 160),
    ("金額",      90),
    ("状態",      80),
    ("発行日",    90),
]


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

        self._table = QTableWidget(0, len(_PAY_COLS))
        self._table.setHorizontalHeaderLabels([c[0] for c in _PAY_COLS])
        hdr = self._table.horizontalHeader()
        hdr.setSortIndicatorShown(True)
        for i, (_, w) in enumerate(_PAY_COLS):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(i, w)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setSortingEnabled(True)
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
            from app.database.models import ProjectMember
            self._table.setSortingEnabled(False)
            self._table.setRowCount(0)
            for iss in issuances:
                row = self._table.rowCount()
                self._table.insertRow(row)
                recipient = iss.recipient_organization or iss.recipient_name or ""
                issued = iss.issued_at.strftime("%Y/%m/%d") if iss.issued_at else ""
                member_number = ""
                org_kana = ""
                if iss.project_member_id:
                    pm = session.get(ProjectMember, iss.project_member_id)
                    if pm:
                        member_number = pm.member_number or ""
                        org_kana = pm.organization_kana or ""
                for col, val in enumerate([
                    iss.doc_number, member_number, recipient, org_kana,
                    f"¥{int(iss.amount):,}", iss.status, issued,
                ]):
                    item = QTableWidgetItem(val)
                    item.setData(Qt.ItemDataRole.UserRole, iss.id)
                    self._table.setItem(row, col, item)
        finally:
            session.close()
        self._table.setSortingEnabled(True)

    def _mark_paid(self):
        row = self._table.currentRow()
        if row < 0:
            return
        issuance_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        dlg = PaymentDialog(issuance_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()


class PaymentDialog(QDialog):
    def __init__(self, issuance_id: int, parent=None, auto_record: bool = True):
        super().__init__(parent)
        self._issuance_id = issuance_id
        self._auto_record = auto_record
        self.setWindowTitle("入金記録")
        self.setFixedSize(360, 260)
        self._build()

    def values(self) -> dict:
        qd = self._date.date()
        return {
            "payment_date": date(qd.year(), qd.month(), qd.day()),
            "amount": self._amount.value(),
            "payment_method": self._method.currentText(),
            "notes": self._notes.text().strip(),
        }

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
        if not self._auto_record:
            self._amount.setReadOnly(True)
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
        if not self._auto_record:
            self.accept()
            return
        v = self.values()
        session = get_session()
        try:
            record_payment(
                session,
                issuance_id=self._issuance_id,
                payment_date=v["payment_date"],
                amount=v["amount"],
                payment_method=v["payment_method"],
                staff_id=current_user.get_id(),
                staff_name=current_user.get_name(),
                notes=v["notes"],
            )
        finally:
            session.close()
        self.accept()
