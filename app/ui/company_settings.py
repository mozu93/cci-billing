# app/ui/company_settings.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QDialog
)
from app.database.connection import get_session
from app.database.models import CompanySettings, BankAccount


def _get_or_create_settings(session) -> CompanySettings:
    cs = session.query(CompanySettings).first()
    if not cs:
        cs = CompanySettings()
        session.add(cs)
        session.commit()
    return cs


class CompanySettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        grp = QGroupBox("発行元情報")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._postal = QLineEdit()
        self._address = QLineEdit()
        self._phone = QLineEdit()
        self._fax = QLineEdit()
        self._email = QLineEdit()
        self._t_number = QLineEdit()
        self._t_number.setPlaceholderText("T1234567890123")
        form.addRow("名称", self._name)
        form.addRow("郵便番号", self._postal)
        form.addRow("住所", self._address)
        form.addRow("電話", self._phone)
        form.addRow("FAX", self._fax)
        form.addRow("メール", self._email)
        form.addRow("インボイス登録番号", self._t_number)
        layout.addWidget(grp)

        btn_save = QPushButton("発行元情報を保存")
        btn_save.clicked.connect(self._save)
        layout.addWidget(btn_save)

        grp2 = QGroupBox("銀行口座")
        bank_layout = QVBoxLayout(grp2)
        self._bank_table = QTableWidget(0, 5)
        self._bank_table.setHorizontalHeaderLabels(
            ["ラベル", "銀行名", "支店名", "口座種別", "口座番号"])
        self._bank_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._bank_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        bank_layout.addWidget(self._bank_table)

        bank_btn_row = QHBoxLayout()
        btn_add_bank = QPushButton("＋ 口座追加")
        btn_add_bank.clicked.connect(self._add_bank)
        btn_del_bank = QPushButton("削除")
        btn_del_bank.clicked.connect(self._del_bank)
        bank_btn_row.addWidget(btn_add_bank)
        bank_btn_row.addWidget(btn_del_bank)
        bank_btn_row.addStretch()
        bank_layout.addLayout(bank_btn_row)
        layout.addWidget(grp2)

    def _load(self):
        session = get_session()
        try:
            cs = _get_or_create_settings(session)
            self._name.setText(cs.name)
            self._postal.setText(cs.postal_code)
            self._address.setText(cs.address)
            self._phone.setText(cs.phone)
            self._fax.setText(cs.fax)
            self._email.setText(cs.email)
            self._t_number.setText(cs.invoice_reg_number)
            self._bank_table.setRowCount(0)
            for b in cs.bank_accounts:
                row = self._bank_table.rowCount()
                self._bank_table.insertRow(row)
                for col, val in enumerate([b.label, b.bank_name, b.bank_branch,
                                            b.bank_account_type, b.bank_account_number]):
                    item = QTableWidgetItem(val)
                    item.setData(0x0100, b.id)
                    self._bank_table.setItem(row, col, item)
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            cs = _get_or_create_settings(session)
            cs.name = self._name.text().strip()
            cs.postal_code = self._postal.text().strip()
            cs.address = self._address.text().strip()
            cs.phone = self._phone.text().strip()
            cs.fax = self._fax.text().strip()
            cs.email = self._email.text().strip()
            cs.invoice_reg_number = self._t_number.text().strip()
            session.commit()
        finally:
            session.close()
        QMessageBox.information(self, "保存", "発行元情報を保存しました。")

    def _add_bank(self):
        dlg = BankAccountDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _del_bank(self):
        row = self._bank_table.currentRow()
        if row < 0:
            return
        bank_id = self._bank_table.item(row, 0).data(0x0100)
        session = get_session()
        try:
            b = session.get(BankAccount, bank_id)
            if b:
                session.delete(b)
                session.commit()
        finally:
            session.close()
        self._load()


class BankAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("銀行口座登録")
        self.setFixedSize(360, 300)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._label = QLineEdit()
        self._label.setPlaceholderText("例：メイン口座")
        self._bank_name = QLineEdit()
        self._branch = QLineEdit()
        self._account_type = QLineEdit("普通")
        self._account_number = QLineEdit()
        self._account_name = QLineEdit()
        form.addRow("ラベル", self._label)
        form.addRow("銀行名", self._bank_name)
        form.addRow("支店名", self._branch)
        form.addRow("口座種別", self._account_type)
        form.addRow("口座番号", self._account_number)
        form.addRow("口座名義", self._account_name)
        layout.addLayout(form)
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("登録")
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _save(self):
        if not self._label.text().strip():
            QMessageBox.warning(self, "入力エラー", "ラベルを入力してください。")
            return
        session = get_session()
        try:
            cs = _get_or_create_settings(session)
            b = BankAccount(
                company_id=cs.id,
                label=self._label.text().strip(),
                bank_name=self._bank_name.text().strip(),
                bank_branch=self._branch.text().strip(),
                bank_account_type=self._account_type.text().strip(),
                bank_account_number=self._account_number.text().strip(),
                bank_account_name=self._account_name.text().strip(),
            )
            session.add(b)
            session.commit()
        finally:
            session.close()
        self.accept()
