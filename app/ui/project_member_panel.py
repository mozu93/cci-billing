# app/ui/project_member_panel.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.services.project_service import (
    get_project_members, add_roster_entries, remove_member_from_project,
    copy_roster_from_project, get_projects
)


class RosterEntryDialog(QDialog):
    """名簿の1エントリ入力ダイアログ"""

    FIELDS = [
        ("organization_name",    "事業所名"),
        ("organization_kana",    "フリガナ（事業所）"),
        ("representative_name",  "代表者名"),
        ("representative_kana",  "代表者フリガナ"),
        ("department",           "所属・役職名"),
        ("postal_code",          "郵便番号"),
        ("address",              "住所"),
        ("phone",                "電話"),
        ("email",                "メール"),
    ]

    def __init__(self, parent=None, initial: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("名簿エントリ")
        self.resize(420, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._fields: dict[str, QLineEdit] = {}
        for key, label in self.FIELDS:
            le = QLineEdit()
            if initial and key in initial:
                le.setText(initial[key] or "")
            self._fields[key] = le
            form.addRow(label + ":", le)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        # ラベルを日本語化
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setText("保存")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("キャンセル")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self):
        org = self._fields["organization_name"].text().strip()
        rep = self._fields["representative_name"].text().strip()
        if not org and not rep:
            QMessageBox.warning(
                self, "入力エラー",
                "事業所名または代表者名のいずれかを入力してください。"
            )
            return
        self.accept()

    def values(self) -> dict:
        return {key: self._fields[key].text() for key, _ in self.FIELDS}


class ProjectCopyDialog(QDialog):
    """他の名簿からコピーするダイアログ"""

    def __init__(self, current_project_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("他の名簿からコピー")
        self.resize(360, 120)
        self._selected_id: int | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("コピー元の名簿を選択してください："))

        self._combo = QComboBox()
        session = get_session()
        try:
            projects = get_projects(session)
        finally:
            session.close()
        for p in projects:
            if p.id == current_project_id:
                continue
            label = f"{p.fiscal_year}年度 {p.name}"
            self._combo.addItem(label, p.id)
        layout.addWidget(self._combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("コピー")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_project_id(self) -> int | None:
        return self._combo.currentData()


class ProjectMemberPanel(QWidget):
    def __init__(self, project_id: int):
        super().__init__()
        self._project_id = project_id
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("名簿"))

        btn_row = QHBoxLayout()
        btn_add = QPushButton("行を追加")
        btn_add.clicked.connect(self._add_entry)
        btn_edit = QPushButton("編集")
        btn_edit.clicked.connect(self._edit_entry)
        btn_copy = QPushButton("他の名簿からコピー")
        btn_copy.clicked.connect(self._copy_from_project)
        btn_import = QPushButton("取り込み（Excel/貼り付け）")
        btn_import.clicked.connect(self._open_import)
        btn_del = QPushButton("削除")
        btn_del.clicked.connect(self._remove)
        for b in [btn_add, btn_edit, btn_copy, btn_import, btn_del]:
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["事業所名", "代表者名", "メール", "電話"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._edit_entry)
        layout.addWidget(self._table)
        self._count_label = QLabel("")
        layout.addWidget(self._count_label)

    def _load(self):
        session = get_session()
        try:
            pms = get_project_members(session, self._project_id)
        finally:
            session.close()
        self._table.setRowCount(0)
        for pm in pms:
            row = self._table.rowCount()
            self._table.insertRow(row)
            vals = [
                pm.organization_name or "",
                pm.representative_name or "",
                pm.email or "",
                pm.phone or "",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, pm.id)
                self._table.setItem(row, col, item)
        self._count_label.setText(f"{len(pms)} 件")

    def _add_entry(self):
        dlg = RosterEntryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_session()
            try:
                add_roster_entries(session, self._project_id, [dlg.values()])
            finally:
                session.close()
            self._load()

    def _edit_entry(self):
        row = self._table.currentRow()
        if row < 0:
            return
        pm_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        session = get_session()
        try:
            from app.database.models import ProjectMember
            pm = session.get(ProjectMember, pm_id)
            if pm is None:
                return
            initial = {
                "organization_name": pm.organization_name,
                "organization_kana": pm.organization_kana,
                "representative_name": pm.representative_name,
                "representative_kana": pm.representative_kana,
                "department": pm.department,
                "postal_code": pm.postal_code,
                "address": pm.address,
                "phone": pm.phone,
                "email": pm.email,
            }
            dlg = RosterEntryDialog(self, initial=initial)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                vals = dlg.values()
                for key, value in vals.items():
                    setattr(pm, key, value)
                session.commit()
        finally:
            session.close()
        self._load()

    def _copy_from_project(self):
        dlg = ProjectCopyDialog(self._project_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            src_id = dlg.selected_project_id()
            if src_id is None:
                return
            session = get_session()
            try:
                copy_roster_from_project(session, src_id, self._project_id)
            finally:
                session.close()
            self._load()

    def _open_import(self):
        from app.ui.roster_import import RosterImportDialog
        dlg = RosterImportDialog(self._project_id, self)
        if dlg.exec():
            self._load()

    def _remove(self):
        row = self._table.currentRow()
        if row < 0:
            return
        pm_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name = self._table.item(row, 0).text()
        if QMessageBox.question(
                self, "削除の確認",
                f"「{name}」をこの名簿から削除します。\nよろしいですか？"
        ) != QMessageBox.StandardButton.Yes:
            return
        session = get_session()
        try:
            remove_member_from_project(session, pm_id)
        finally:
            session.close()
        self._load()
