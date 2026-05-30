# app/ui/member_form.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QCheckBox, QTextEdit, QPushButton, QLabel, QMessageBox
)
from app.database.connection import get_session
from app.services.member_service import create_member, update_member_name, get_member_by_id


class MemberFormDialog(QDialog):
    def __init__(self, member_id: int | None = None, parent=None):
        super().__init__(parent)
        self._member_id = member_id
        self.setWindowTitle("会員登録" if member_id is None else "会員編集")
        self.setFixedSize(480, 500)
        self._build()
        if member_id:
            self._load(member_id)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("※ 事業所名または代表者名のどちらか一方は必須"))
        form = QFormLayout()

        self._member_number = QLineEdit()
        self._member_number.setPlaceholderText("例：A-001（任意）")
        self._org_name = QLineEdit()
        self._org_kana = QLineEdit()
        self._rep_name = QLineEdit()
        self._rep_kana = QLineEdit()
        self._postal = QLineEdit()
        self._address = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._is_member = QCheckBox("会員")
        self._is_member.setChecked(True)
        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)

        form.addRow("会員番号", self._member_number)
        form.addRow("事業所名 *", self._org_name)
        form.addRow("事業所名フリガナ", self._org_kana)
        form.addRow("代表者名", self._rep_name)
        form.addRow("代表者名フリガナ", self._rep_kana)
        form.addRow("郵便番号", self._postal)
        form.addRow("住所", self._address)
        form.addRow("電話", self._phone)
        form.addRow("メール", self._email)
        form.addRow("区分", self._is_member)
        form.addRow("備考", self._notes)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("保存")
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _load(self, member_id: int):
        session = get_session()
        try:
            m = get_member_by_id(session, member_id)
            if m:
                self._member_number.setText(m.member_number or "")
                self._org_name.setText(m.organization_name)
                self._org_kana.setText(m.organization_kana)
                self._rep_name.setText(m.representative_name)
                self._rep_kana.setText(m.representative_kana)
                self._postal.setText(m.postal_code)
                self._address.setText(m.address)
                self._phone.setText(m.phone)
                self._email.setText(m.email)
                self._is_member.setChecked(m.is_member)
                self._notes.setPlainText(m.notes)
        finally:
            session.close()

    def _save(self):
        org = self._org_name.text().strip()
        rep = self._rep_name.text().strip()
        if not org and not rep:
            QMessageBox.warning(self, "入力エラー", "事業所名または代表者名を入力してください。")
            return
        session = get_session()
        try:
            if self._member_id is None:
                create_member(
                    session,
                    member_number=self._member_number.text().strip() or None,
                    organization_name=org,
                    organization_kana=self._org_kana.text().strip(),
                    representative_name=rep,
                    representative_kana=self._rep_kana.text().strip(),
                    postal_code=self._postal.text().strip(),
                    address=self._address.text().strip(),
                    phone=self._phone.text().strip(),
                    email=self._email.text().strip(),
                    is_member=self._is_member.isChecked(),
                    notes=self._notes.toPlainText().strip()
                )
            else:
                update_member_name(
                    session, self._member_id,
                    new_organization_name=org,
                    new_organization_kana=self._org_kana.text().strip(),
                    new_representative_name=rep,
                    new_representative_kana=self._rep_kana.text().strip(),
                    reason="手動編集"
                )
        finally:
            session.close()
        self.accept()
