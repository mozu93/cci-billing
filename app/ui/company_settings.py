# app/ui/company_settings.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QDialog,
    QFileDialog, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.database.models import CompanySettings, BankAccount, SealImage


def _ask_label(parent, title: str, prompt: str, default: str = "") -> tuple[str, bool]:
    from PyQt6.QtWidgets import QInputDialog
    text, ok = QInputDialog.getText(parent, title, prompt, text=default)
    return text.strip() or default, ok


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
        root = QHBoxLayout(self)
        root.setSpacing(12)

        # ── 左カラム：発行元情報 ──────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        grp = QGroupBox("発行元情報")
        form = QFormLayout(grp)
        form.setSpacing(6)
        self._name    = QLineEdit()
        self._postal  = QLineEdit()
        self._postal.setMaximumWidth(120)
        self._address = QLineEdit()
        self._phone   = QLineEdit()
        self._fax     = QLineEdit()
        self._email   = QLineEdit()
        self._t_number = QLineEdit()
        self._t_number.setPlaceholderText("T1234567890123")
        form.addRow("名称",               self._name)
        form.addRow("郵便番号",           self._postal)
        form.addRow("住所",               self._address)
        form.addRow("電話",               self._phone)
        form.addRow("FAX",                self._fax)
        form.addRow("メール",             self._email)
        form.addRow("インボイス登録番号", self._t_number)
        left.addWidget(grp)

        btn_save = QPushButton("発行元情報を保存")
        btn_save.setFixedHeight(34)
        btn_save.clicked.connect(self._save)
        left.addWidget(btn_save)
        left.addStretch()

        root.addLayout(left, 4)   # 左4割

        # ── 右カラム：銀行口座 ＋ 印鑑画像 ───────────────
        right = QVBoxLayout()
        right.setSpacing(10)

        # 銀行口座
        grp2 = QGroupBox("銀行口座")
        bank_layout = QVBoxLayout(grp2)
        bank_layout.setSpacing(6)
        self._bank_table = QTableWidget(0, 5)
        self._bank_table.setHorizontalHeaderLabels(
            ["ラベル", "銀行名", "支店名", "種別", "口座番号"])
        self._bank_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._bank_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self._bank_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._bank_table.setMaximumHeight(150)
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
        right.addWidget(grp2)

        # 印鑑画像
        grp3 = QGroupBox("印鑑画像")
        seal_layout = QVBoxLayout(grp3)
        seal_layout.setSpacing(6)
        seal_layout.addWidget(QLabel(
            "PNG / JPG を登録。★デフォルトが領収書に印刷されます。"))
        self._print_seal_chk = QCheckBox("印鑑を印字する（請求書・領収書共通）")
        self._print_seal_chk.setChecked(True)
        self._print_seal_chk.stateChanged.connect(self._save_seal_option)
        seal_layout.addWidget(self._print_seal_chk)

        self._seal_table = QTableWidget(0, 3)
        self._seal_table.setHorizontalHeaderLabels(["ラベル", "ファイルパス", ""])
        self._seal_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._seal_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self._seal_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self._seal_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._seal_table.setMaximumHeight(150)
        seal_layout.addWidget(self._seal_table)

        seal_btn_row = QHBoxLayout()
        btn_add_seal     = QPushButton("＋ 画像を登録")
        btn_default_seal = QPushButton("★ デフォルトに設定")
        btn_del_seal     = QPushButton("削除")
        btn_add_seal.clicked.connect(self._add_seal)
        btn_default_seal.clicked.connect(self._set_default_seal)
        btn_del_seal.clicked.connect(self._del_seal)
        seal_btn_row.addWidget(btn_add_seal)
        seal_btn_row.addWidget(btn_default_seal)
        seal_btn_row.addWidget(btn_del_seal)
        seal_btn_row.addStretch()
        seal_layout.addLayout(seal_btn_row)
        right.addWidget(grp3)
        right.addStretch()

        root.addLayout(right, 6)   # 右6割

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
            self._print_seal_chk.blockSignals(True)
            self._print_seal_chk.setChecked(
                bool(cs.print_seal) if cs.print_seal is not None else True)
            self._print_seal_chk.blockSignals(False)
            self._bank_table.setRowCount(0)
            for b in cs.bank_accounts:
                row = self._bank_table.rowCount()
                self._bank_table.insertRow(row)
                for col, val in enumerate([b.label, b.bank_name, b.bank_branch,
                                            b.bank_account_type, b.bank_account_number]):
                    item = QTableWidgetItem(val)
                    item.setData(0x0100, b.id)
                    self._bank_table.setItem(row, col, item)

            self._seal_table.setRowCount(0)
            for s in cs.seal_images:
                row = self._seal_table.rowCount()
                self._seal_table.insertRow(row)
                default_mark = "★ デフォルト" if s.is_default else ""
                for col, val in enumerate([s.label, s.path, default_mark]):
                    item = QTableWidgetItem(val)
                    item.setData(0x0100, s.id)
                    self._seal_table.setItem(row, col, item)
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

    def _save_seal_option(self):
        session = get_session()
        try:
            cs = _get_or_create_settings(session)
            cs.print_seal = self._print_seal_chk.isChecked()
            session.commit()
        finally:
            session.close()

    def _add_seal(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "印鑑画像を選択", "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path:
            return
        label, ok = _ask_label(self, "印鑑ラベル", "印鑑のラベルを入力してください：",
                                default="印鑑")
        if not ok:
            return
        session = get_session()
        try:
            cs = _get_or_create_settings(session)
            is_first = session.query(SealImage).filter_by(
                company_id=cs.id).count() == 0
            seal = SealImage(
                company_id=cs.id,
                label=label,
                path=path,
                is_default=is_first,
            )
            session.add(seal)
            session.commit()
        finally:
            session.close()
        self._load()

    def _set_default_seal(self):
        row = self._seal_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "未選択", "デフォルトにする印鑑を選択してください。")
            return
        seal_id = self._seal_table.item(row, 0).data(0x0100)
        session = get_session()
        try:
            cs = _get_or_create_settings(session)
            for s in cs.seal_images:
                s.is_default = (s.id == seal_id)
            session.commit()
        finally:
            session.close()
        self._load()

    def _del_seal(self):
        row = self._seal_table.currentRow()
        if row < 0:
            return
        seal_id = self._seal_table.item(row, 0).data(0x0100)
        label = self._seal_table.item(row, 0).text()
        if QMessageBox.question(
                self, "削除の確認",
                f"印鑑画像「{label}」を削除します。\nよろしいですか？"
        ) != QMessageBox.StandardButton.Yes:
            return
        session = get_session()
        try:
            s = session.get(SealImage, seal_id)
            if s:
                session.delete(s)
                session.commit()
        finally:
            session.close()
        self._load()

    def _add_bank(self):
        dlg = BankAccountDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _del_bank(self):
        row = self._bank_table.currentRow()
        if row < 0:
            return
        bank_id = self._bank_table.item(row, 0).data(0x0100)
        bank_name = self._bank_table.item(row, 1).text()
        if QMessageBox.question(
                self, "削除の確認",
                f"口座「{bank_name}」を削除します。\nよろしいですか？"
        ) != QMessageBox.StandardButton.Yes:
            return
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
