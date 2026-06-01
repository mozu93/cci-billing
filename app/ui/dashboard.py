# app/ui/dashboard.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from app.database.connection import get_session
from app.services.project_service import get_projects, get_project_progress


class DashboardWidget(QWidget):
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
        btn_refresh = QPushButton("更新")
        btn_refresh.clicked.connect(self._load)
        top_row.addWidget(self._year_combo)
        top_row.addWidget(btn_refresh)
        btn_rollover = QPushButton("年度更新")
        btn_rollover.clicked.connect(self._rollover)
        top_row.addWidget(btn_rollover)
        top_row.addStretch()
        layout.addLayout(top_row)

        layout.addWidget(QLabel("■ 受付中の事業"))
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["事業名", "種別", "全件", "発行済", "支払済", "未発行"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)


    def _load(self):
        year = self._year_combo.currentData()
        session = get_session()
        try:
            active = get_projects(session, fiscal_year=year, status="active")

            self._table.setRowCount(0)
            for proj in active:
                p = get_project_progress(session, proj.id)
                row = self._table.rowCount()
                self._table.insertRow(row)
                type_label = "リスト型" if proj.project_type == "list" else "窓口型"
                pending = p["pending"]
                for col, val in enumerate([
                    proj.name, type_label,
                    str(p["total"]), str(p["issued"]),
                    str(p["paid"]), str(pending)
                ]):
                    item = QTableWidgetItem(val)
                    item.setData(Qt.ItemDataRole.UserRole, proj.id)
                    if col == 5 and pending > 0:
                        item.setForeground(QColor("#DC2626"))
                    self._table.setItem(row, col, item)
        finally:
            session.close()

    def _rollover(self):
        from app.ui.fiscal_year_dialog import FiscalYearDialog
        from PyQt6.QtWidgets import QDialog
        dlg = FiscalYearDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()
