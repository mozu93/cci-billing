# app/ui/project_form.py
from datetime import date
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QTextEdit,
    QPushButton, QLabel, QMessageBox, QListWidget,
    QListWidgetItem, QGroupBox
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.services.category_service import get_active_categories
from app.services.item_template_service import get_templates_by_category
from app.services.project_service import (
    create_project, get_project_by_id,
    add_template_to_project, get_project_templates
)


class ProjectFormDialog(QDialog):
    def __init__(self, project_id: int | None = None, parent=None):
        super().__init__(parent)
        self._project_id = project_id
        self.setWindowTitle("事業登録" if project_id is None else "事業編集")
        self.resize(560, 580)
        self._build()
        if project_id:
            self._load(project_id)

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit()
        self._name.setPlaceholderText("例：2026年度 青年部会費")
        self._category = QComboBox()
        self._category.currentIndexChanged.connect(self._on_category_change)
        self._fiscal_year = QSpinBox()
        self._fiscal_year.setRange(2000, 2099)
        self._fiscal_year.setValue(date.today().year)
        self._project_type = QComboBox()
        self._project_type.addItems(["リスト型（会員名簿あり）", "窓口型（その場入力）"])
        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)

        form.addRow("事業名", self._name)
        form.addRow("カテゴリ", self._category)
        form.addRow("年度", self._fiscal_year)
        form.addRow("種別", self._project_type)
        form.addRow("備考", self._notes)
        layout.addLayout(form)

        grp = QGroupBox("請求項目テンプレート（1つ以上必須）")
        grp_layout = QHBoxLayout(grp)

        left = QVBoxLayout()
        left.addWidget(QLabel("利用可能なテンプレート："))
        self._avail_list = QListWidget()
        left.addWidget(self._avail_list)
        btn_add_tmpl = QPushButton("→ 追加")
        btn_add_tmpl.clicked.connect(self._add_template)
        left.addWidget(btn_add_tmpl)

        right = QVBoxLayout()
        right.addWidget(QLabel("この事業で使用するテンプレート："))
        self._selected_list = QListWidget()
        right.addWidget(self._selected_list)
        btn_del_tmpl = QPushButton("← 削除")
        btn_del_tmpl.clicked.connect(self._remove_template)
        right.addWidget(btn_del_tmpl)

        grp_layout.addLayout(left)
        grp_layout.addLayout(right)
        layout.addWidget(grp)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("保存")
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        session = get_session()
        try:
            for cat in get_active_categories(session):
                self._category.addItem(cat.name, cat.id)
        finally:
            session.close()

    def _on_category_change(self, _):
        cat_id = self._category.currentData()
        if cat_id is None:
            return
        session = get_session()
        try:
            templates = get_templates_by_category(session, cat_id)
        finally:
            session.close()
        self._avail_list.clear()
        for t in templates:
            item = QListWidgetItem(f"{t.name}（¥{int(t.unit_price):,}）")
            item.setData(Qt.ItemDataRole.UserRole, t.id)
            self._avail_list.addItem(item)

    def _add_template(self):
        item = self._avail_list.currentItem()
        if not item:
            return
        tmpl_id = item.data(Qt.ItemDataRole.UserRole)
        for i in range(self._selected_list.count()):
            if self._selected_list.item(i).data(Qt.ItemDataRole.UserRole) == tmpl_id:
                return
        new_item = QListWidgetItem(item.text())
        new_item.setData(Qt.ItemDataRole.UserRole, tmpl_id)
        self._selected_list.addItem(new_item)

    def _remove_template(self):
        row = self._selected_list.currentRow()
        if row >= 0:
            self._selected_list.takeItem(row)

    def _load(self, project_id: int):
        session = get_session()
        try:
            proj = get_project_by_id(session, project_id)
            if not proj:
                return
            self._name.setText(proj.name)
            self._fiscal_year.setValue(proj.fiscal_year)
            self._project_type.setCurrentIndex(0 if proj.project_type == "list" else 1)
            self._notes.setPlainText(proj.notes or "")
            for i in range(self._category.count()):
                if self._category.itemData(i) == proj.category_id:
                    self._category.setCurrentIndex(i)
                    break
            for pt in get_project_templates(session, project_id):
                tmpl = pt.item_template
                item = QListWidgetItem(f"{tmpl.name}（¥{int(tmpl.unit_price):,}）")
                item.setData(Qt.ItemDataRole.UserRole, tmpl.id)
                self._selected_list.addItem(item)
        finally:
            session.close()

    def _save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "入力エラー", "事業名を入力してください。")
            return
        if self._selected_list.count() == 0:
            QMessageBox.warning(self, "入力エラー", "テンプレートを1つ以上選択してください。")
            return
        session = get_session()
        try:
            ptype = "list" if self._project_type.currentIndex() == 0 else "counter"
            if self._project_id is None:
                proj = create_project(
                    session, name=name,
                    category_id=self._category.currentData(),
                    fiscal_year=self._fiscal_year.value(),
                    project_type=ptype,
                    notes=self._notes.toPlainText().strip()
                )
                for i in range(self._selected_list.count()):
                    tmpl_id = self._selected_list.item(i).data(Qt.ItemDataRole.UserRole)
                    add_template_to_project(session, proj.id, tmpl_id, sort_order=i)
            else:
                proj = get_project_by_id(session, self._project_id)
                proj.name = name
                proj.category_id = self._category.currentData()
                proj.fiscal_year = self._fiscal_year.value()
                proj.project_type = ptype
                proj.notes = self._notes.toPlainText().strip()
                from app.database.models import ProjectTemplate
                session.query(ProjectTemplate).filter_by(project_id=proj.id).delete()
                session.commit()
                for i in range(self._selected_list.count()):
                    tmpl_id = self._selected_list.item(i).data(Qt.ItemDataRole.UserRole)
                    add_template_to_project(session, proj.id, tmpl_id, sort_order=i)
        finally:
            session.close()
        self.accept()
