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
from app.services.category_service import get_active_categories, create_category
from app.services.item_template_service import get_templates_by_category
from app.services.project_service import (
    create_project, get_project_by_id,
    add_template_to_project, get_project_templates
)


class ProjectFormDialog(QDialog):
    def __init__(self, project_id: int | None = None, parent=None):
        super().__init__(parent)
        self._project_id = project_id
        self.setWindowTitle("請求・領収書データの登録" if project_id is None
                            else "請求・領収書データの編集")
        self.resize(560, 580)
        self._build()
        if project_id:
            self._load(project_id)

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._category = QComboBox()
        self._category.currentIndexChanged.connect(self._on_category_change)
        self._fiscal_year = QSpinBox()
        self._fiscal_year.setRange(2000, 2099)
        self._fiscal_year.setValue(date.today().year)
        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)

        cat_row = QHBoxLayout()
        cat_row.addWidget(self._category)
        btn_new_cat = QPushButton("＋ 新規業務名…")
        btn_new_cat.setFixedWidth(120)
        btn_new_cat.clicked.connect(self._add_category_master)
        cat_row.addWidget(btn_new_cat)
        form.addRow("業務名", cat_row)
        self._title = QLineEdit()
        self._title.setPlaceholderText("件名（例：2026 視察研修会参加費）")
        form.addRow("件名", self._title)
        form.addRow("年度", self._fiscal_year)
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
        btn_new_tmpl = QPushButton("＋ 新規テンプレート…")
        btn_new_tmpl.clicked.connect(self._add_template_master)
        left.addWidget(btn_new_tmpl)

        right = QVBoxLayout()
        right.addWidget(QLabel("この名簿で使用するテンプレート："))
        self._selected_list = QListWidget()
        right.addWidget(self._selected_list)
        btn_del_tmpl = QPushButton("← 削除")
        btn_del_tmpl.clicked.connect(self._remove_template)
        right.addWidget(btn_del_tmpl)

        grp_layout.addLayout(left)
        grp_layout.addLayout(right)
        layout.addWidget(grp)

        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("プレビュー種別："))
        self._doc_type = QComboBox()
        self._doc_type.addItem("請求書", "invoice")
        self._doc_type.addItem("領収書", "receipt")
        preview_row.addWidget(self._doc_type)
        btn_preview = QPushButton("プレビュー（宛先空）")
        btn_preview.clicked.connect(self._preview)
        preview_row.addWidget(btn_preview)
        preview_row.addStretch()
        layout.addLayout(preview_row)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("保存")
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        self._reload_categories()

    def _reload_categories(self, select_id: int | None = None):
        self._category.blockSignals(True)
        self._category.clear()
        session = get_session()
        try:
            for cat in get_active_categories(session):
                self._category.addItem(cat.name, cat.id)
        finally:
            session.close()
        if select_id is not None:
            for i in range(self._category.count()):
                if self._category.itemData(i) == select_id:
                    self._category.setCurrentIndex(i)
                    break
        self._category.blockSignals(False)
        self._on_category_change(None)

    def _add_category_master(self):
        from app.ui.category_management import CategoryEditDialog
        dlg = CategoryEditDialog(self)
        dlg.setWindowTitle("業務名の新規追加")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, sort_order = dlg.values()
        if not name:
            QMessageBox.warning(self, "入力エラー", "業務名を入力してください。")
            return
        session = get_session()
        try:
            cat = create_category(session, name, sort_order)
            new_id = cat.id
        finally:
            session.close()
        self._reload_categories(select_id=new_id)

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

    def _add_template_master(self):
        """その場で新規テンプレートをマスタ登録し、利用可能一覧へ反映する。"""
        from app.ui.item_template_management import ItemTemplateDialog
        dlg = ItemTemplateDialog(self, default_category_id=self._category.currentData())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._on_category_change(None)

    def _load(self, project_id: int):
        session = get_session()
        try:
            proj = get_project_by_id(session, project_id)
            if not proj:
                return
            self._title.setText(proj.name or "")
            self._fiscal_year.setValue(proj.fiscal_year)
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

    def _preview(self):
        if self._selected_list.count() == 0:
            QMessageBox.warning(self, "プレビュー不可",
                                "請求項目テンプレートを1つ以上選択してください。")
            return
        from app.database.models import ItemTemplate
        from app.utils import pdf_helpers
        session = get_session()
        try:
            lines_data = []
            for i in range(self._selected_list.count()):
                tmpl_id = self._selected_list.item(i).data(Qt.ItemDataRole.UserRole)
                t = session.get(ItemTemplate, tmpl_id)
                if t is None:
                    continue
                lines_data.append({
                    "item_template_id": t.id,
                    "item_name": t.name,
                    "quantity": 1,
                    "unit": t.unit,
                    "unit_price": int(t.unit_price),
                    "tax_rate": t.tax_rate,
                })
            try:
                result = pdf_helpers.generate_preview(
                    lines_data, self._doc_type.currentData(), session)
                if result is None:
                    QMessageBox.warning(
                        self, "プレビュー不可",
                        "自社情報（会社設定）が未登録のためプレビューできません。\n"
                        "設定 → 会社情報 から登録してください。")
            except Exception as e:
                QMessageBox.critical(self, "プレビューエラー", str(e))
        finally:
            session.close()

    def _save(self):
        cat_id = self._category.currentData()
        business = self._category.currentText().strip()
        title = self._title.text().strip()
        if not business or cat_id is None:
            QMessageBox.warning(self, "入力エラー", "業務名を選択してください。")
            return
        if not title:
            QMessageBox.warning(self, "入力エラー", "件名を入力してください。")
            return
        if self._selected_list.count() == 0:
            QMessageBox.warning(self, "入力エラー", "テンプレートを1つ以上選択してください。")
            return
        session = get_session()
        try:
            if self._project_id is None:
                proj = create_project(
                    session, name=title,
                    category_id=cat_id,
                    fiscal_year=self._fiscal_year.value(),
                    project_type="list",
                    notes=self._notes.toPlainText().strip()
                )
                for i in range(self._selected_list.count()):
                    tmpl_id = self._selected_list.item(i).data(Qt.ItemDataRole.UserRole)
                    add_template_to_project(session, proj.id, tmpl_id, sort_order=i)
            else:
                proj = get_project_by_id(session, self._project_id)
                proj.name = title
                proj.category_id = cat_id
                proj.fiscal_year = self._fiscal_year.value()
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
