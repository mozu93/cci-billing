# app/ui/category_management.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.services.category_service import (
    create_category, get_active_categories, deactivate_category
)


class CategoryManagementWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        add_row = QHBoxLayout()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("業務名（例：青年部）")
        self._order_input = QSpinBox()
        self._order_input.setRange(0, 999)
        btn_add = QPushButton("追加")
        btn_add.clicked.connect(self._add)
        add_row.addWidget(QLabel("名称："))
        add_row.addWidget(self._name_input)
        add_row.addWidget(QLabel("表示順："))
        add_row.addWidget(self._order_input)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        self._list = QListWidget()
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        btn_del = QPushButton("削除（無効化）")
        btn_del.clicked.connect(self._deactivate)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _load(self):
        session = get_session()
        try:
            cats = get_active_categories(session)
        finally:
            session.close()
        self._list.clear()
        for c in cats:
            item = QListWidgetItem(f"{c.name}（表示順:{c.sort_order}）")
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self._list.addItem(item)

    def _add(self):
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "入力エラー", "業務名を入力してください。")
            return
        session = get_session()
        try:
            create_category(session, name, self._order_input.value())
        finally:
            session.close()
        self._name_input.clear()
        self._load()

    def _deactivate(self):
        item = self._list.currentItem()
        if not item:
            return
        cat_id = item.data(Qt.ItemDataRole.UserRole)
        session = get_session()
        try:
            deactivate_category(session, cat_id)
        finally:
            session.close()
        self._load()
