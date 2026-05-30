# app/ui/login_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.services.staff_service import get_active_staff
from app.utils import current_user


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ログイン")
        self.setFixedSize(320, 400)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("担当者を選択してください"))

        self._list = QListWidget()
        session = get_session()
        try:
            for staff in get_active_staff(session):
                item = QListWidgetItem(staff.name)
                item.setData(Qt.ItemDataRole.UserRole, (staff.id, staff.name))
                self._list.addItem(item)
        finally:
            session.close()

        self._list.itemDoubleClicked.connect(self._login)
        layout.addWidget(self._list)

        btn = QPushButton("ログイン")
        btn.clicked.connect(self._login)
        layout.addWidget(btn)

    def _login(self):
        item = self._list.currentItem()
        if not item:
            QMessageBox.warning(self, "選択エラー", "担当者を選択してください。")
            return
        staff_id, staff_name = item.data(Qt.ItemDataRole.UserRole)
        current_user.set_current(staff_id, staff_name)
        self.accept()
