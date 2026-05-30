# app/ui/issuance_from_project.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QComboBox, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from app.database.connection import get_session
from app.services.project_service import (
    get_projects, get_project_members, get_project_by_id, get_project_templates
)
from app.services.issuance_service import create_issuance_for_member, mark_as_issued
from app.utils import current_user


class IssuanceFromProjectWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load_projects()

    def _build(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("事業："))
        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(300)
        self._proj_combo.currentIndexChanged.connect(self._load_members)
        top.addWidget(self._proj_combo)
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["未発行のみ", "すべて"])
        self._filter_combo.currentIndexChanged.connect(self._load_members)
        top.addWidget(QLabel("表示："))
        top.addWidget(self._filter_combo)
        top.addStretch()
        layout.addLayout(top)

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("名前・会員番号で絞り込み")
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._load_members)
        self._search.textChanged.connect(lambda: self._timer.start(300))
        search_row.addWidget(QLabel("検索："))
        search_row.addWidget(self._search)
        layout.addLayout(search_row)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["会員番号", "事業所名", "代表者名", "ステータス", "発行番号"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_prepare = QPushButton("準備（採番）")
        btn_prepare.clicked.connect(self._prepare)
        btn_issue = QPushButton("発行する")
        btn_issue.clicked.connect(self._issue)
        self._delivery_combo = QComboBox()
        self._delivery_combo.addItems(["窓口手渡し", "郵送", "メール送付", "その他"])
        btn_row.addWidget(btn_prepare)
        btn_row.addWidget(btn_issue)
        btn_row.addWidget(QLabel("配付方法："))
        btn_row.addWidget(self._delivery_combo)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

    def _load_projects(self):
        session = get_session()
        try:
            projects = get_projects(session, status="active")
        finally:
            session.close()
        self._proj_combo.clear()
        for p in projects:
            self._proj_combo.addItem(p.name, p.id)
        self._load_members()

    def _load_members(self):
        project_id = self._proj_combo.currentData()
        if project_id is None:
            self._table.setRowCount(0)
            return
        query = self._search.text().strip().lower()
        show_all = self._filter_combo.currentIndex() == 1
        session = get_session()
        try:
            pms = get_project_members(session, project_id)
            from app.database.models import Issuance
            pm_data = []
            for pm in pms:
                m = pm.member
                if not m:
                    continue
                iss = (session.query(Issuance)
                       .filter_by(project_member_id=pm.id)
                       .order_by(Issuance.created_at.desc())
                       .first())
                status = iss.status if iss else "未準備"
                doc_number = iss.doc_number if iss else ""
                issuance_id = iss.id if iss else None
                if not show_all and status in ("発行済み", "支払済み"):
                    continue
                if query:
                    targets = [m.member_number or "", m.organization_name,
                               m.representative_name, m.organization_kana]
                    if not any(query in t.lower() for t in targets):
                        continue
                pm_data.append((pm.id, m, status, doc_number, issuance_id))
        finally:
            session.close()

        self._table.setRowCount(0)
        for pm_id, m, status, doc_number, issuance_id in pm_data:
            row = self._table.rowCount()
            self._table.insertRow(row)
            for col, val in enumerate([
                m.member_number or "", m.organization_name,
                m.representative_name, status, doc_number
            ]):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, (pm_id, issuance_id))
                self._table.setItem(row, col, item)
        self._status_label.setText(f"{len(pm_data)} 件表示")

    def _selected_pm(self) -> tuple[int, int | None] | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        return self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _get_doc_type(self, session, project_id: int) -> str:
        pts = get_project_templates(session, project_id)
        for pt in pts:
            if pt.item_template.doc_type in ("receipt",):
                return "receipt"
        return "invoice"

    def _prepare(self):
        sel = self._selected_pm()
        if sel is None:
            return
        pm_id, issuance_id = sel
        if issuance_id is not None:
            QMessageBox.information(self, "情報", "既に採番済みです。")
            return
        project_id = self._proj_combo.currentData()
        session = get_session()
        try:
            from app.database.models import ProjectMember
            pm = session.get(ProjectMember, pm_id)
            m = pm.member
            today = date.today()
            doc_type = self._get_doc_type(session, project_id)
            create_issuance_for_member(
                session, project_id=project_id,
                project_member_id=pm_id,
                member=m, doc_type=doc_type,
                fiscal_year=today.year, month=today.month
            )
        finally:
            session.close()
        self._load_members()

    def _issue(self):
        sel = self._selected_pm()
        if sel is None:
            return
        pm_id, issuance_id = sel
        if issuance_id is None:
            QMessageBox.warning(self, "エラー", "先に「準備（採番）」を行ってください。")
            return
        delivery = self._delivery_combo.currentText()
        session = get_session()
        try:
            from app.database.models import Issuance
            iss = session.get(Issuance, issuance_id)
            if iss and iss.status == "発行済み":
                # 再発行：既存PDFを開く or 再生成
                from app.utils.pdf_helpers import generate_and_open
                generate_and_open(iss, session)
                return
            mark_as_issued(session, issuance_id,
                           staff_id=current_user.get_id(),
                           staff_name=current_user.get_name(),
                           delivery_method=delivery)
            iss = session.get(Issuance, issuance_id)
            from app.utils.pdf_helpers import generate_and_open
            generate_and_open(iss, session)
        except Exception as e:
            QMessageBox.critical(self, "PDF生成エラー", str(e))
        finally:
            session.close()
        self._load_members()
