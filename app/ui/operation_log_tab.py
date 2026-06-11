# app/ui/operation_log_tab.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QComboBox, QPushButton, QHeaderView, QDateEdit, QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from app.database.connection import get_session
from app.database.models import OperationLog


_ACTIONS = ["すべて", "発行", "内容修正", "再発行", "入金記録", "メール送信", "メール送信失敗", "督促メール送信"]

_COLS = [
    ("日時",     180),
    ("担当者",    90),
    ("操作",      80),
    ("詳細",       0),  # stretch
]


class OperationLogWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._rows: list[dict] = []
        self._build()

    def showEvent(self, event):
        super().showEvent(event)
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("開始日："))
        self._from_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self._from_date.setCalendarPopup(True)
        self._from_date.dateChanged.connect(self._load)
        top.addWidget(self._from_date)

        top.addWidget(QLabel("終了日："))
        self._to_date = QDateEdit(QDate.currentDate())
        self._to_date.setCalendarPopup(True)
        self._to_date.dateChanged.connect(self._load)
        top.addWidget(self._to_date)

        top.addWidget(QLabel("操作："))
        self._action_combo = QComboBox()
        self._action_combo.addItems(_ACTIONS)
        self._action_combo.currentIndexChanged.connect(self._load)
        top.addWidget(self._action_combo)

        btn_csv = QPushButton("CSV出力")
        btn_csv.clicked.connect(self._export_csv)
        top.addWidget(btn_csv)
        top.addStretch()
        layout.addLayout(top)

        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels([c[0] for c in _COLS])
        hdr = self._table.horizontalHeader()
        for i, (_, w) in enumerate(_COLS):
            if w == 0:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self._table.setColumnWidth(i, w)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#555; font-size:11px;")
        layout.addWidget(self._count_lbl)

    def _load(self):
        from datetime import datetime, time
        fd = self._from_date.date()
        td = self._to_date.date()
        from_dt = datetime(fd.year(), fd.month(), fd.day(), 0, 0, 0)
        to_dt   = datetime(td.year(), td.month(), td.day(), 23, 59, 59)
        action  = self._action_combo.currentText()

        session = get_session()
        try:
            q = (session.query(OperationLog)
                 .filter(OperationLog.created_at >= from_dt)
                 .filter(OperationLog.created_at <= to_dt))
            if action != "すべて":
                q = q.filter(OperationLog.action == action)
            logs = q.order_by(OperationLog.created_at.desc()).all()
            self._rows = [
                {
                    "日時":   l.created_at.strftime("%Y/%m/%d %H:%M:%S"),
                    "担当者": l.staff_name or "",
                    "操作":   l.action,
                    "詳細":   l.detail or "",
                }
                for l in logs
            ]
        finally:
            session.close()

        self._table.setRowCount(0)
        for row in self._rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            for col, key in enumerate(["日時", "担当者", "操作", "詳細"]):
                self._table.setItem(r, col, QTableWidgetItem(row[key]))
        self._count_lbl.setText(f"{len(self._rows)} 件")

    def _export_csv(self):
        if not self._rows:
            QMessageBox.information(self, "情報", "データがありません。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "CSV保存", "", "CSV (*.csv)")
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["日時", "担当者", "操作", "詳細"])
            writer.writeheader()
            writer.writerows(self._rows)
        QMessageBox.information(self, "完了", f"CSVを保存しました。\n{path}")
