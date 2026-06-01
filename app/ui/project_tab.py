# app/ui/project_tab.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QHeaderView, QDialog, QSplitter
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.services.project_service import (
    get_projects, close_project, reopen_project,
    get_project_progress, get_project_by_id
)
from app.ui.project_form import ProjectFormDialog
from app.ui.project_member_panel import ProjectMemberPanel


class ProjectTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("年度："))
        self._year_combo = QComboBox()
        current_year = date.today().year
        for y in range(current_year + 1, current_year - 5, -1):
            self._year_combo.addItem(f"{y}年度", y)
        self._year_combo.setCurrentIndex(1)
        self._year_combo.currentIndexChanged.connect(self._load)
        top_row.addWidget(self._year_combo)

        btn_add = QPushButton("＋ 新規名簿登録")
        btn_add.clicked.connect(self._add)
        btn_edit = QPushButton("編集")
        btn_edit.clicked.connect(self._edit)
        top_row.addWidget(btn_add)
        top_row.addWidget(btn_edit)
        top_row.addStretch()

        self._status_combo = QComboBox()
        self._status_combo.addItem("受付中", "active")
        self._status_combo.addItem("完了", "closed")
        self._status_combo.addItem("すべて", None)
        self._status_combo.setCurrentIndex(0)
        self._status_combo.currentIndexChanged.connect(self._load)
        top_row.addWidget(QLabel("状態："))
        top_row.addWidget(self._status_combo)
        layout.addLayout(top_row)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["名簿名", "状態", "全件", "発行済", "未発行"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.currentCellChanged.connect(self._on_select)
        splitter.addWidget(self._table)

        self._member_panel_container = QWidget()
        from PyQt6.QtWidgets import QVBoxLayout as VL
        self._member_panel_layout = VL(self._member_panel_container)
        splitter.addWidget(self._member_panel_container)
        splitter.setSizes([300, 300])
        layout.addWidget(splitter)

        btn_row2 = QHBoxLayout()
        btn_close = QPushButton("完了")
        btn_close.clicked.connect(self._close)
        btn_reopen = QPushButton("完了を戻す")
        btn_reopen.clicked.connect(self._reopen)
        for b in [btn_close, btn_reopen]:
            btn_row2.addWidget(b)
        btn_row2.addStretch()
        layout.addLayout(btn_row2)

    def _load(self):
        year = self._year_combo.currentData()
        status = self._status_combo.currentData()
        session = get_session()
        try:
            projects = get_projects(session, fiscal_year=year, status=status)
            self._table.setRowCount(0)
            for proj in projects:
                p = get_project_progress(session, proj.id)
                row = self._table.rowCount()
                self._table.insertRow(row)
                for col, val in enumerate([
                    proj.name, proj.status,
                    str(p["total"]), str(p["issued"]), str(p["pending"])
                ]):
                    item = QTableWidgetItem(val)
                    item.setData(Qt.ItemDataRole.UserRole, proj.id)
                    self._table.setItem(row, col, item)
        finally:
            session.close()

    def _on_select(self, row, *_):
        if row < 0:
            return
        project_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        session = get_session()
        try:
            proj = get_project_by_id(session, project_id)
            project_type = proj.project_type if proj else "list"
        finally:
            session.close()
        for i in reversed(range(self._member_panel_layout.count())):
            w = self._member_panel_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        if project_type == "list":
            panel = ProjectMemberPanel(project_id)
            self._member_panel_layout.addWidget(panel)

    def _selected_project_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        return self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _add(self):
        dlg = ProjectFormDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _edit(self):
        pid = self._selected_project_id()
        if pid is None:
            return
        dlg = ProjectFormDialog(project_id=pid, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _close(self):
        pid = self._selected_project_id()
        if pid is None:
            return
        session = get_session()
        try:
            close_project(session, pid)
        finally:
            session.close()
        self._load()

    def _reopen(self):
        pid = self._selected_project_id()
        if pid is None:
            return
        session = get_session()
        try:
            reopen_project(session, pid)
        finally:
            session.close()
        self._load()
