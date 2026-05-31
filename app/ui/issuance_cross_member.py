# app/ui/issuance_cross_member.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QComboBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from app.database.connection import get_session
from app.services.member_service import search_members
from app.services.issuance_service import (
    get_pending_issuances_for_project_member, create_combined_issuance
)
from app.services.project_service import get_project_by_id
from app.utils import current_user


class IssuanceCrossMemberWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._member = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "会員を検索して選択すると、全事業の未発行一覧が表示されます。\n"
            "チェックした項目をまとめて発行できます（同種別のみ合算可）。"
        ))

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("会員番号・事業所名・フリガナ・代表者名")
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._search_member)
        self._search.textChanged.connect(lambda: self._timer.start(300))
        search_row.addWidget(QLabel("検索："))
        search_row.addWidget(self._search)
        layout.addLayout(search_row)

        self._member_table = QTableWidget(0, 3)
        self._member_table.setHorizontalHeaderLabels(["会員番号", "事業所名", "代表者名"])
        self._member_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._member_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._member_table.setMaximumHeight(120)
        self._member_table.currentCellChanged.connect(self._on_member_select)
        layout.addWidget(self._member_table)

        layout.addWidget(QLabel("未発行一覧（全事業横断）："))
        self._pending_table = QTableWidget(0, 4)
        self._pending_table.setHorizontalHeaderLabels(
            ["選択", "事業名", "書類種別", "金額"])
        self._pending_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._pending_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._pending_table)

        btn_row = QHBoxLayout()
        self._delivery_combo = QComboBox()
        self._delivery_combo.addItems(["窓口手渡し", "郵送", "メール送付", "その他"])
        btn_issue = QPushButton("選択した項目を発行する")
        btn_issue.clicked.connect(self._issue)
        btn_row.addWidget(QLabel("配付方法："))
        btn_row.addWidget(self._delivery_combo)
        btn_row.addWidget(btn_issue)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _search_member(self):
        query = self._search.text().strip()
        if not query:
            return
        session = get_session()
        try:
            members = search_members(session, query)[:10]
        finally:
            session.close()
        self._member_table.setRowCount(0)
        for m in members:
            row = self._member_table.rowCount()
            self._member_table.insertRow(row)
            for col, val in enumerate([
                m.member_number or "", m.organization_name, m.representative_name
            ]):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, m.id)
                self._member_table.setItem(row, col, item)

    def _on_member_select(self, row, *_):
        if row < 0:
            return
        member_id = self._member_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        session = get_session()
        try:
            from app.database.models import Member
            self._member = session.get(Member, member_id)
            pending = get_pending_issuances_for_project_member(session, member_id)
            self._pending_table.setRowCount(0)
            for iss in pending:
                proj = get_project_by_id(session, iss.project_id)
                r = self._pending_table.rowCount()
                self._pending_table.insertRow(r)
                cb = QCheckBox()
                cb.setChecked(True)
                self._pending_table.setCellWidget(r, 0, cb)
                doc_label = "請求書" if iss.doc_type == "invoice" else "領収書"
                for col, val in enumerate(
                        [proj.name if proj else "", doc_label,
                         f"¥{int(iss.amount):,}"], 1):
                    item = QTableWidgetItem(val)
                    item.setData(Qt.ItemDataRole.UserRole,
                                 (iss.id, iss.project_id,
                                  iss.project_member_id, iss.doc_type))
                    self._pending_table.setItem(r, col, item)
        finally:
            session.close()

    def _issue(self):
        if self._member is None:
            QMessageBox.warning(self, "エラー", "会員を選択してください。")
            return
        invoice_items = []
        receipt_items = []
        for row in range(self._pending_table.rowCount()):
            cb = self._pending_table.cellWidget(row, 0)
            if not (cb and cb.isChecked()):
                continue
            data = self._pending_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            iss_id, proj_id, pm_id, doc_type = data
            item = {"issuance_id": iss_id, "project_id": proj_id,
                    "project_member_id": pm_id, "quantity": 1}
            if doc_type == "invoice":
                invoice_items.append(item)
            else:
                receipt_items.append(item)

        if not invoice_items and not receipt_items:
            QMessageBox.warning(self, "エラー", "発行する項目を選択してください。")
            return

        today = date.today()
        delivery = self._delivery_combo.currentText()
        session = get_session()
        try:
            for items, doc_type in [(invoice_items, "invoice"),
                                    (receipt_items, "receipt")]:
                if not items:
                    continue
                create_combined_issuance(
                    session,
                    issuances_data=items,
                    doc_type=doc_type,
                    recipient_organization=self._member.organization_name,
                    recipient_name=self._member.representative_name,
                    fiscal_year=today.year,
                    month=today.month,
                    staff_id=current_user.get_id(),
                    staff_name=current_user.get_name(),
                    delivery_method=delivery
                )
        finally:
            session.close()
        QMessageBox.information(self, "発行完了", "発行しました。")
        self._on_member_select(self._member_table.currentRow())
