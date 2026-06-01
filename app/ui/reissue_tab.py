# app/ui/reissue_tab.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.database.models import Issuance, Project
from sqlalchemy.orm import joinedload

COL_NUM  = 0
COL_PROJ = 1
COL_DEST = 2
COL_AMT  = 3
COL_TYPE = 4
COL_STAT = 5
COL_DATE = 6

_TYPE_LABEL = {"invoice": "請求書", "receipt": "領収書"}
_STAT_LABEL = {"発行済み": "発行済み", "支払済み": "支払済み", "準備中": "準備中"}


class ReissueWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("年度："))
        self._year_combo = QComboBox()
        y = date.today().year
        self._year_combo.addItem("すべて", None)
        for yr in range(y + 1, y - 5, -1):
            self._year_combo.addItem(f"{yr}年度", yr)
        self._year_combo.setCurrentIndex(2)
        self._year_combo.currentIndexChanged.connect(self._load)
        top.addWidget(self._year_combo)

        btn_refresh = QPushButton("更新")
        btn_refresh.clicked.connect(self._load)
        top.addWidget(btn_refresh)
        top.addStretch()

        self._btn_reissue = QPushButton("再発行（PDF再出力）")
        self._btn_reissue.setFixedHeight(36)
        self._btn_reissue.setStyleSheet(
            "QPushButton { background:#1D4ED8; color:white; border-radius:4px;"
            " font-weight:bold; padding:0 16px; }"
            "QPushButton:hover { background:#1E40AF; }"
        )
        self._btn_reissue.clicked.connect(self._reissue)
        top.addWidget(self._btn_reissue)
        layout.addLayout(top)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["発行番号", "名簿名", "宛先", "金額", "種別", "状態", "発行日"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(COL_PROJ, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_DEST, QHeaderView.ResizeMode.Stretch)
        for col in (COL_NUM, COL_AMT, COL_TYPE, COL_STAT, COL_DATE):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#555; font-size:11px;")
        layout.addWidget(self._count_lbl)

    def _load(self):
        year = self._year_combo.currentData()
        session = get_session()
        try:
            q = (session.query(Issuance, Project)
                 .join(Project, Issuance.project_id == Project.id)
                 .filter(Issuance.status.in_(["発行済み", "支払済み"])))
            if year:
                q = q.filter(Project.fiscal_year == year)
            rows = q.order_by(Issuance.issued_at.desc()).all()
        finally:
            session.close()

        self._table.setRowCount(0)
        for iss, proj in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            dest = (iss.recipient_organization or iss.recipient_name or "").strip()
            issued = (iss.issued_at.strftime("%Y/%m/%d")
                      if iss.issued_at else "")
            for col, val in [
                (COL_NUM,  iss.doc_number or ""),
                (COL_PROJ, proj.name or ""),
                (COL_DEST, dest),
                (COL_AMT,  f"¥{int(iss.amount):,}"),
                (COL_TYPE, _TYPE_LABEL.get(iss.doc_type, iss.doc_type)),
                (COL_STAT, iss.status),
                (COL_DATE, issued),
            ]:
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, iss.id)
                self._table.setItem(r, col, item)

        self._count_lbl.setText(f"{len(rows)} 件")

    def _reissue(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "未選択",
                                    "再発行する行を選択してください。")
            return
        iss_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        doc_num = self._table.item(row, COL_NUM).text()

        session = get_session()
        try:
            iss = (session.query(Issuance)
                   .options(joinedload(Issuance.lines))
                   .filter_by(id=iss_id)
                   .first())
            if not iss:
                QMessageBox.critical(self, "エラー", "発行データが見つかりません。")
                return
            from app.utils.pdf_helpers import generate_and_open
            generate_and_open(iss, session, reissue=True)
        except Exception as e:
            QMessageBox.critical(self, "再発行エラー", str(e))
        finally:
            session.close()
