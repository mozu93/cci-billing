# app/ui/staff_management.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.services.staff_service import (
    create_staff, get_all_staff, deactivate_staff, reactivate_staff
)


class StaffManagementWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        add_row = QHBoxLayout()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("スタッフ名を入力")
        btn_add = QPushButton("追加")
        btn_add.clicked.connect(self._add)
        add_row.addWidget(QLabel("氏名："))
        add_row.addWidget(self._name_input)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["ID", "氏名", "状態"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_deact = QPushButton("無効化")
        btn_deact.clicked.connect(self._deactivate)
        btn_react = QPushButton("有効化")
        btn_react.clicked.connect(self._reactivate)
        btn_row.addWidget(btn_deact)
        btn_row.addWidget(btn_react)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _load(self):
        session = get_session()
        try:
            staff_list = get_all_staff(session)
        finally:
            session.close()
        self._table.setRowCount(0)
        for s in staff_list:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(str(s.id)))
            self._table.setItem(row, 1, QTableWidgetItem(s.name))
            self._table.setItem(row, 2, QTableWidgetItem("有効" if s.is_active else "無効"))

    def _add(self):
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "入力エラー", "氏名を入力してください。")
            return
        session = get_session()
        try:
            create_staff(session, name)
        except Exception as e:
            QMessageBox.critical(self, "エラー", str(e))
            return
        finally:
            session.close()
        self._name_input.clear()
        self._load()

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        return int(self._table.item(row, 0).text())

    def _deactivate(self):
        staff_id = self._selected_id()
        if staff_id is None:
            return
        name = self._table.item(self._table.currentRow(), 1).text()
        if QMessageBox.question(
                self, "無効化の確認",
                f"スタッフ「{name}」を無効化します。\nよろしいですか？"
        ) != QMessageBox.StandardButton.Yes:
            return
        session = get_session()
        try:
            deactivate_staff(session, staff_id)
        finally:
            session.close()
        self._load()

    def _reactivate(self):
        staff_id = self._selected_id()
        if staff_id is None:
            return
        session = get_session()
        try:
            reactivate_staff(session, staff_id)
        finally:
            session.close()
        self._load()
