# app/ui/project_member_panel.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QDialog,
    QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.services.project_service import (
    get_project_members, add_members_to_project, remove_member_from_project
)
from app.services.member_service import search_members
from app.utils.excel_utils import parse_tsv_text, parse_excel_file


class ProjectMemberPanel(QWidget):
    def __init__(self, project_id: int):
        super().__init__()
        self._project_id = project_id
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("会員リスト（リスト型事業）"))

        btn_row = QHBoxLayout()
        btn_import = QPushButton("Excelインポート")
        btn_import.clicked.connect(self._import)
        btn_paste = QPushButton("貼り付けインポート")
        btn_paste.clicked.connect(self._paste_import)
        btn_del = QPushButton("削除")
        btn_del.clicked.connect(self._remove)
        for b in [btn_import, btn_paste, btn_del]:
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["会員番号", "事業所名", "代表者名", "ステータス"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)
        self._count_label = QLabel("")
        layout.addWidget(self._count_label)

    def _load(self):
        session = get_session()
        try:
            pms = get_project_members(session, self._project_id)
            from app.database.models import Issuance
            pm_status = {}
            for pm in pms:
                iss = (session.query(Issuance)
                       .filter_by(project_member_id=pm.id)
                       .order_by(Issuance.created_at.desc())
                       .first())
                pm_status[pm.id] = iss.status if iss else "未準備"
        finally:
            session.close()
        self._table.setRowCount(0)
        for pm in pms:
            m = pm.member
            row = self._table.rowCount()
            self._table.insertRow(row)
            vals = [
                m.member_number or "" if m else "",
                m.organization_name if m else "",
                m.representative_name if m else "",
                pm_status.get(pm.id, "未準備")
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, pm.id)
                self._table.setItem(row, col, item)
        self._count_label.setText(f"{len(pms)} 件")

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excelを選択", "", "Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            rows = parse_excel_file(path)
            self._register_rows(rows)
        except Exception as e:
            QMessageBox.critical(self, "エラー", str(e))

    def _paste_import(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("貼り付けインポート")
        dlg.resize(600, 200)
        from PyQt6.QtWidgets import QVBoxLayout as VL
        vl = VL(dlg)
        te = QTextEdit()
        te.setPlaceholderText("ExcelからコピーしてCtrl+Vで貼り付け")
        vl.addWidget(te)
        btn = QPushButton("インポート")
        btn.clicked.connect(dlg.accept)
        vl.addWidget(btn)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            rows = parse_tsv_text(te.toPlainText())
            self._register_rows(rows)

    def _register_rows(self, rows: list[dict]):
        session = get_session()
        added = 0
        try:
            for row in rows:
                key = row.get("member_number", "") or row.get("organization_name", "")
                if not key:
                    continue
                members = search_members(session, key)
                if members:
                    add_members_to_project(session, self._project_id, [members[0].id])
                    added += 1
        finally:
            session.close()
        QMessageBox.information(self, "完了", f"{added} 件を追加しました。")
        self._load()

    def _remove(self):
        row = self._table.currentRow()
        if row < 0:
            return
        pm_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        session = get_session()
        try:
            remove_member_from_project(session, pm_id)
        finally:
            session.close()
        self._load()
