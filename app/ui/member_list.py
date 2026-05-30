# app/ui/member_list.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from app.database.connection import get_session
from app.services.member_service import search_members, deactivate_member
from app.ui.member_form import MemberFormDialog
from app.ui.member_import import MemberImportDialog


class MemberListWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load("")

    def _build(self):
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("会員番号・事業所名・フリガナ・代表者名で検索")
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(lambda: self._load(self._search.text()))
        self._search.textChanged.connect(lambda: self._search_timer.start(300))
        search_row.addWidget(QLabel("検索："))
        search_row.addWidget(self._search)
        layout.addLayout(search_row)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("＋ 新規登録")
        btn_add.clicked.connect(self._add)
        btn_edit = QPushButton("編集")
        btn_edit.clicked.connect(self._edit)
        btn_del = QPushButton("無効化")
        btn_del.clicked.connect(self._deactivate)
        btn_import = QPushButton("Excelインポート")
        btn_import.clicked.connect(self._import)
        for b in [btn_add, btn_edit, btn_del, btn_import]:
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["会員番号", "事業所名", "代表者名", "電話", "区分"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.itemDoubleClicked.connect(self._edit)
        layout.addWidget(self._table)

        self._count_label = QLabel("")
        layout.addWidget(self._count_label)

    def _load(self, query: str):
        session = get_session()
        try:
            members = search_members(session, query)
        finally:
            session.close()
        self._table.setRowCount(0)
        for m in members:
            row = self._table.rowCount()
            self._table.insertRow(row)
            for col, val in enumerate([
                m.member_number or "",
                m.organization_name,
                m.representative_name,
                m.phone,
                "会員" if m.is_member else "非会員"
            ]):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, m.id)
                self._table.setItem(row, col, item)
        self._count_label.setText(f"{len(members)} 件")

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        return self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _add(self):
        dlg = MemberFormDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load(self._search.text())

    def _edit(self):
        member_id = self._selected_id()
        if member_id is None:
            return
        dlg = MemberFormDialog(member_id=member_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load(self._search.text())

    def _deactivate(self):
        member_id = self._selected_id()
        if member_id is None:
            return
        session = get_session()
        try:
            deactivate_member(session, member_id)
        finally:
            session.close()
        self._load(self._search.text())

    def _import(self):
        dlg = MemberImportDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load(self._search.text())
