# app/ui/issuance_cross_member.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from app.database.connection import get_session
from app.services.issuance_service import (
    search_unpaid_invoices, issue_receipt_for_invoice
)
from app.services.project_service import get_project_by_id
from app.ui.payment_dialog import PaymentDialog
from app.utils import current_user
from app.utils.pdf_helpers import generate_and_open


class IssuanceCrossMemberWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "事業所を検索すると、発行済みで未入金の請求書が一覧に出ます。\n"
            "行を選んで入金を記録すると、その請求書の領収書を発行します。"
        ))

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("事業所名・フリガナ・代表者名")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._search_member)
        self._search.textChanged.connect(lambda: self._timer.start(300))
        search_row.addWidget(QLabel("検索："))
        search_row.addWidget(self._search)
        layout.addLayout(search_row)

        layout.addWidget(QLabel("発行済み・未入金の請求書："))
        self._result_table = QTableWidget(0, 5)
        self._result_table.setHorizontalHeaderLabels(
            ["事業所名", "件名", "請求書番号", "金額", "発行日"])
        self._result_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._result_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._result_table)

        btn_row = QHBoxLayout()
        btn_issue = QPushButton("入金を記録して領収書を発行")
        btn_issue.clicked.connect(self._issue_receipt)
        btn_row.addWidget(btn_issue)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _search_member(self):
        query = self._search.text().strip()
        self._result_table.setRowCount(0)
        if not query:
            return
        session = get_session()
        try:
            invoices = search_unpaid_invoices(session, query)
            for iss in invoices:
                proj = get_project_by_id(session, iss.project_id)
                row = self._result_table.rowCount()
                self._result_table.insertRow(row)
                issued = iss.issued_at.strftime("%Y/%m/%d") if iss.issued_at else ""
                values = [
                    iss.recipient_organization or iss.recipient_name or "",
                    proj.name if proj else "",
                    iss.doc_number,
                    f"¥{int(iss.amount):,}",
                    issued,
                ]
                for col, val in enumerate(values):
                    item = QTableWidgetItem(val)
                    item.setData(Qt.ItemDataRole.UserRole, iss.id)
                    self._result_table.setItem(row, col, item)
        finally:
            session.close()

    def _selected_invoice_id(self) -> int | None:
        row = self._result_table.currentRow()
        if row < 0:
            return None
        return self._result_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _issue_receipt(self):
        invoice_id = self._selected_invoice_id()
        if invoice_id is None:
            QMessageBox.warning(self, "未選択", "請求書を選択してください。")
            return
        dlg = PaymentDialog(invoice_id, self, auto_record=False)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        session = get_session()
        try:
            receipt = issue_receipt_for_invoice(
                session, invoice_id=invoice_id,
                payment_date=v["payment_date"],
                payment_method=v["payment_method"],
                notes=v["notes"],
                staff_id=current_user.get_id(),
                staff_name=current_user.get_name(),
            )
            pdf_path = generate_and_open(receipt, session)
        except Exception as e:
            QMessageBox.critical(self, "エラー", str(e))
        else:
            if pdf_path is None:
                QMessageBox.information(
                    self, "領収書を発行しました",
                    "入金を記録し領収書を登録しましたが、自社情報が未登録のため"
                    "PDFを生成できませんでした。設定で自社情報を登録してください。")
        finally:
            session.close()
        self._search_member()
