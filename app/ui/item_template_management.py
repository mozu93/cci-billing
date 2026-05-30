# app/ui/item_template_management.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QSpinBox, QDialog,
    QFormLayout, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.services.category_service import get_active_categories
from app.services.item_template_service import (
    create_item_template, get_all_active_templates, deactivate_item_template
)

TAX_RATE_OPTIONS = [("消費税10%", 10), ("消費税8%", 8), ("非課税", 0), ("不課税", -1)]
DOC_TYPE_OPTIONS = [("請求書・領収書両方", "both"), ("請求書のみ", "invoice"), ("領収書のみ", "receipt")]


class ItemTemplateManagementWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("＋ 新規テンプレート")
        btn_add.clicked.connect(self._add)
        btn_del = QPushButton("無効化")
        btn_del.clicked.connect(self._deactivate)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["カテゴリ", "項目名", "単価", "単位", "税区分", "書類種別"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

    def _load(self):
        session = get_session()
        try:
            templates = get_all_active_templates(session)
            rows = []
            for t in templates:
                cat_name = t.category.name if t.category else ""
                tax_label = next((l for l, v in TAX_RATE_OPTIONS if v == t.tax_rate), str(t.tax_rate))
                doc_label = next((l for l, v in DOC_TYPE_OPTIONS if v == t.doc_type), t.doc_type)
                rows.append((t.id, cat_name, t.name, f"¥{int(t.unit_price):,}",
                              t.unit, tax_label, doc_label))
        finally:
            session.close()
        self._table.setRowCount(0)
        for tmpl_id, *vals in rows:
            row = self._table.rowCount()
            self._table.insertRow(row)
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, tmpl_id)
                self._table.setItem(row, col, item)

    def _add(self):
        dlg = ItemTemplateDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _deactivate(self):
        row = self._table.currentRow()
        if row < 0:
            return
        tmpl_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        session = get_session()
        try:
            deactivate_item_template(session, tmpl_id)
        finally:
            session.close()
        self._load()


class ItemTemplateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("請求項目テンプレート登録")
        self.setFixedSize(400, 360)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._category = QComboBox()
        session = get_session()
        try:
            for cat in get_active_categories(session):
                self._category.addItem(cat.name, cat.id)
        finally:
            session.close()

        self._name = QLineEdit()
        self._name.setPlaceholderText("例：青年部会費")
        self._unit_price = QSpinBox()
        self._unit_price.setRange(0, 9999999)
        self._unit = QLineEdit("式")
        self._tax_rate = QComboBox()
        for label, value in TAX_RATE_OPTIONS:
            self._tax_rate.addItem(label, value)
        self._doc_type = QComboBox()
        for label, value in DOC_TYPE_OPTIONS:
            self._doc_type.addItem(label, value)
        self._description = QLineEdit()
        self._description.setPlaceholderText("但し書き（領収書に使用）")

        form.addRow("カテゴリ", self._category)
        form.addRow("項目名", self._name)
        form.addRow("単価（円）", self._unit_price)
        form.addRow("単位", self._unit)
        form.addRow("税区分", self._tax_rate)
        form.addRow("書類種別", self._doc_type)
        form.addRow("但し書き", self._description)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("登録")
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "入力エラー", "項目名を入力してください。")
            return
        if self._category.currentData() is None:
            QMessageBox.warning(self, "入力エラー",
                                "カテゴリが選択されていません。\n"
                                "先に「設定→カテゴリ」でカテゴリを登録してください。")
            return
        session = get_session()
        try:
            create_item_template(
                session,
                category_id=self._category.currentData(),
                name=name,
                unit_price=self._unit_price.value(),
                unit=self._unit.text().strip() or "式",
                tax_rate=self._tax_rate.currentData(),
                doc_type=self._doc_type.currentData(),
                description=self._description.text().strip()
            )
        except Exception as e:
            QMessageBox.critical(self, "保存エラー", str(e))
            return
        finally:
            session.close()
        self.accept()
