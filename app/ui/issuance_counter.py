# app/ui/issuance_counter.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QComboBox, QLabel, QPushButton,
    QMessageBox, QGroupBox
)
from app.database.connection import get_session
from app.services.project_service import get_projects, get_project_by_id
from app.services.issuance_service import create_counter_issuance
from app.utils import current_user


class IssuanceCounterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load_projects()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("窓口型事業：宛先・数量を入力して即発行します。"))

        form = QFormLayout()
        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(300)
        self._proj_combo.currentIndexChanged.connect(self._on_project_change)
        self._org_name = QLineEdit()
        self._org_name.setPlaceholderText("事業所名（任意）")
        self._rep_name = QLineEdit()
        self._rep_name.setPlaceholderText("代表者名・個人名（任意）")
        self._quantity = QSpinBox()
        self._quantity.setRange(1, 9999)
        self._quantity.setValue(1)
        self._quantity.valueChanged.connect(self._update_amount)
        self._delivery_combo = QComboBox()
        self._delivery_combo.addItems(["窓口手渡し", "郵送", "メール送付", "その他"])

        form.addRow("事業", self._proj_combo)
        form.addRow("事業所名", self._org_name)
        form.addRow("代表者名/個人名", self._rep_name)
        form.addRow("数量", self._quantity)
        form.addRow("配付方法", self._delivery_combo)
        layout.addLayout(form)

        self._amount_label = QLabel("金額：¥0")
        self._amount_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #2563EB;")
        layout.addWidget(self._amount_label)

        grp = QGroupBox("明細プレビュー")
        grp_layout = QVBoxLayout(grp)
        self._preview_label = QLabel("")
        self._preview_label.setWordWrap(True)
        grp_layout.addWidget(self._preview_label)
        layout.addWidget(grp)

        btn = QPushButton("発行する")
        btn.setFixedHeight(40)
        btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        btn.clicked.connect(self._issue)
        layout.addWidget(btn)
        layout.addStretch()

    def _load_projects(self):
        session = get_session()
        try:
            projects = [p for p in get_projects(session, status="active")
                        if p.project_type == "counter"]
        finally:
            session.close()
        self._proj_combo.clear()
        for p in projects:
            self._proj_combo.addItem(p.name, p.id)
        self._on_project_change()

    def _on_project_change(self):
        self._update_amount()
        self._update_preview()

    def _get_unit_price(self) -> int:
        project_id = self._proj_combo.currentData()
        if project_id is None:
            return 0
        session = get_session()
        try:
            from app.database.models import ProjectTemplate
            pts = session.query(ProjectTemplate).filter_by(project_id=project_id).all()
            return sum(int(pt.unit_price_override or pt.item_template.unit_price)
                       for pt in pts)
        finally:
            session.close()

    def _update_amount(self):
        price = self._get_unit_price()
        self._amount_label.setText(f"金額：¥{price * self._quantity.value():,}")

    def _update_preview(self):
        project_id = self._proj_combo.currentData()
        if project_id is None:
            self._preview_label.setText("")
            return
        session = get_session()
        try:
            from app.database.models import ProjectTemplate
            pts = session.query(ProjectTemplate).filter_by(project_id=project_id).all()
            lines = [f"・{pt.item_template.name}  "
                     f"¥{int(pt.unit_price_override or pt.item_template.unit_price):,}"
                     f"/{pt.item_template.unit}"
                     for pt in pts]
        finally:
            session.close()
        self._preview_label.setText("\n".join(lines))

    def _issue(self):
        org = self._org_name.text().strip()
        rep = self._rep_name.text().strip()
        if not org and not rep:
            QMessageBox.warning(self, "入力エラー",
                                "事業所名または代表者名を入力してください。")
            return
        project_id = self._proj_combo.currentData()
        if project_id is None:
            QMessageBox.warning(self, "エラー", "事業を選択してください。")
            return
        today = date.today()
        session = get_session()
        try:
            from app.database.models import ProjectTemplate
            pt = session.query(ProjectTemplate).filter_by(
                project_id=project_id).first()
            doc_type = "receipt"
            if pt and pt.item_template.doc_type == "invoice":
                doc_type = "invoice"
            iss = create_counter_issuance(
                session,
                project_id=project_id,
                recipient_organization=org,
                recipient_name=rep,
                doc_type=doc_type,
                quantity=self._quantity.value(),
                fiscal_year=today.year,
                month=today.month
            )
            iss.staff_id = current_user.get_id()
            iss.staff_name = current_user.get_name()
            iss.delivery_method = self._delivery_combo.currentText()
            session.commit()
        finally:
            session.close()
        QMessageBox.information(self, "発行完了",
                                "発行しました。\nPDF印刷はPlan 3で実装されます。")
        self._org_name.clear()
        self._rep_name.clear()
        self._quantity.setValue(1)
