# app/ui/reissue_tab.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QHeaderView, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer
from app.database.connection import get_session
from app.database.models import Issuance, Project
from app.services.project_service import get_projects
from app.services.category_service import get_active_categories
from sqlalchemy.orm import joinedload

COL_NUM  = 0
COL_PROJ = 1
COL_DEST = 2
COL_AMT  = 3
COL_TYPE = 4
COL_STAT = 5
COL_DATE = 6

_TYPE_LABEL = {"invoice": "請求書", "receipt": "領収書"}


class ReissueWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._all_projects: list = []
        self._build()
        self._load_filter_data()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_filter_data()

    def _build(self):
        layout = QVBoxLayout(self)

        # ── フィルタ行 ────────────────────────────────────────────────
        top = QHBoxLayout()

        top.addWidget(QLabel("年度："))
        self._year_combo = QComboBox()
        self._year_combo.setMinimumWidth(95)
        y = date.today().year
        self._year_combo.addItem("すべて", None)
        for yr in range(y + 1, y - 5, -1):
            self._year_combo.addItem(f"{yr}年度", yr)
        self._year_combo.setCurrentIndex(2)
        self._year_combo.currentIndexChanged.connect(self._on_year_cat_changed)
        top.addWidget(self._year_combo)

        top.addWidget(QLabel("業務区分："))
        self._cat_combo = QComboBox()
        self._cat_combo.setMinimumWidth(120)
        self._cat_combo.currentIndexChanged.connect(self._on_year_cat_changed)
        top.addWidget(self._cat_combo)

        top.addWidget(QLabel("件名："))
        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(220)
        self._proj_combo.currentIndexChanged.connect(self._load)
        top.addWidget(self._proj_combo)

        top.addWidget(QLabel("種別："))
        self._type_combo = QComboBox()
        self._type_combo.addItem("すべて",  None)
        self._type_combo.addItem("請求書", "invoice")
        self._type_combo.addItem("領収書", "receipt")
        self._type_combo.currentIndexChanged.connect(self._load)
        top.addWidget(self._type_combo)

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

        # ── 検索行 ───────────────────────────────────────────────────
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("宛先・件名で絞り込み")
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_search)
        self._search.textChanged.connect(lambda: self._search_timer.start(300))
        search_row.addWidget(QLabel("検索："))
        search_row.addWidget(self._search)
        layout.addLayout(search_row)

        # ── テーブル ─────────────────────────────────────────────────
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["発行番号", "件名", "宛先", "金額", "種別", "状態", "発行日"])
        hdr = self._table.horizontalHeader()
        hdr.setSortIndicatorShown(True)
        hdr.setSectionResizeMode(COL_PROJ, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_DEST, QHeaderView.ResizeMode.Stretch)
        for col in (COL_NUM, COL_AMT, COL_TYPE, COL_STAT, COL_DATE):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#555; font-size:11px;")
        layout.addWidget(self._count_lbl)

    # ── フィルタデータ初期化 ──────────────────────────────────────────

    def _load_filter_data(self):
        session = get_session()
        try:
            self._all_projects = get_projects(session)   # counter除外・全ステータス
            cats = get_active_categories(session)
        finally:
            session.close()

        used_cat_ids = {p.category_id for p in self._all_projects}
        current_cat = self._cat_combo.currentData()
        self._cat_combo.blockSignals(True)
        self._cat_combo.clear()
        self._cat_combo.addItem("すべて", None)
        for c in cats:
            if c.id in used_cat_ids:
                self._cat_combo.addItem(c.name, c.id)
        for i in range(self._cat_combo.count()):
            if self._cat_combo.itemData(i) == current_cat:
                self._cat_combo.setCurrentIndex(i)
                break
        self._cat_combo.blockSignals(False)

        self._refresh_proj_combo()

    def _on_year_cat_changed(self):
        self._refresh_proj_combo()

    def _refresh_proj_combo(self):
        sel_year = self._year_combo.currentData()
        sel_cat  = self._cat_combo.currentData()
        current_id = self._proj_combo.currentData()

        self._proj_combo.blockSignals(True)
        self._proj_combo.clear()
        self._proj_combo.addItem("すべて", None)
        for p in self._all_projects:
            if sel_year is not None and p.fiscal_year != sel_year:
                continue
            if sel_cat is not None and p.category_id != sel_cat:
                continue
            self._proj_combo.addItem(p.name, p.id)
        for i in range(self._proj_combo.count()):
            if self._proj_combo.itemData(i) == current_id:
                self._proj_combo.setCurrentIndex(i)
                break
        self._proj_combo.blockSignals(False)
        self._load()

    # ── データ読み込み ────────────────────────────────────────────────

    def _load(self):
        year     = self._year_combo.currentData()
        proj_id  = self._proj_combo.currentData()
        doc_type = self._type_combo.currentData()

        session = get_session()
        try:
            q = (session.query(Issuance, Project)
                 .join(Project, Issuance.project_id == Project.id)
                 .filter(Issuance.status.in_(["発行済み", "支払済み"])))
            if year:
                q = q.filter(Project.fiscal_year == year)
            if proj_id:
                q = q.filter(Issuance.project_id == proj_id)
            if doc_type:
                q = q.filter(Issuance.doc_type == doc_type)
            rows = q.order_by(Issuance.issued_at.desc()).all()
        finally:
            session.close()

        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for iss, proj in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            dest = (iss.recipient_organization or iss.recipient_name or "").strip()
            issued = iss.issued_at.strftime("%Y/%m/%d") if iss.issued_at else ""
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

        self._table.setSortingEnabled(True)
        self._count_lbl.setText(f"{len(rows)} 件")
        self._apply_search()

    # ── 検索（クライアント側フィルタ） ───────────────────────────────

    def _apply_search(self):
        q = self._search.text().strip().lower()
        total = 0
        for r in range(self._table.rowCount()):
            if not q:
                self._table.setRowHidden(r, False)
                total += 1
                continue
            targets = []
            for col in (COL_PROJ, COL_DEST):  # 件名, 宛先
                it = self._table.item(r, col)
                if it:
                    targets.append(it.text().lower())
            hidden = not any(q in t for t in targets)
            self._table.setRowHidden(r, hidden)
            if not hidden:
                total += 1
        self._count_lbl.setText(f"{total} 件")

    # ── 再発行 ───────────────────────────────────────────────────────

    def _reissue(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "未選択",
                                    "再発行する行を選択してください。")
            return
        iss_id = self._table.item(row, COL_NUM).data(Qt.ItemDataRole.UserRole)

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
            due_date = None
            if iss.doc_type == "invoice":
                from app.ui.invoice_options_dialog import InvoiceOptionsDialog
                from PyQt6.QtWidgets import QDialog
                opts = InvoiceOptionsDialog(issued_at=iss.issued_at, parent=self)
                if opts.exec() != QDialog.DialogCode.Accepted:
                    return
                due_date = opts.due_date()
            generate_and_open(iss, session, reissue=True, due_date=due_date)
        except Exception as e:
            QMessageBox.critical(self, "再発行エラー", str(e))
        finally:
            session.close()
