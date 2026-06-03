# app/ui/report_tab.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QComboBox, QLabel,
    QPushButton, QHeaderView, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from app.database.connection import get_session
from app.database.models import Issuance
from app.services.report_service import (
    get_unpaid_report, get_payment_report,
    get_project_summary, export_to_excel
)


class ReportTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        inner = QTabWidget()
        inner.addTab(UnpaidReportWidget(), "未払い一覧")
        inner.addTab(PaymentReportWidget(), "入金一覧")
        inner.addTab(ProjectSummaryWidget(), "名簿別集計")
        layout.addWidget(inner)


class _BaseReportWidget(QWidget):
    HEADERS: list[str] = []
    KEYS: list[str] = []

    def __init__(self):
        super().__init__()
        self._build()
        self._load()

    def showEvent(self, event):
        # タブを開くたびに最新の内容を表示する（更新ボタン不要）
        super().showEvent(event)
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("年度："))
        self._year_combo = QComboBox()
        current_year = date.today().year
        self._year_combo.addItem("すべて", None)
        for y in range(current_year + 1, current_year - 5, -1):
            self._year_combo.addItem(f"{y}年度", y)
        self._year_combo.setCurrentIndex(2)
        self._year_combo.currentIndexChanged.connect(self._load)
        top.addWidget(self._year_combo)
        btn_csv = QPushButton("CSV出力")
        btn_csv.clicked.connect(self._export_csv)
        top.addWidget(btn_csv)
        btn_excel = QPushButton("Excel出力")
        btn_excel.clicked.connect(self._export_excel)
        top.addWidget(btn_excel)
        self._add_actions(top)
        top.addStretch()
        layout.addLayout(top)
        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        layout.addWidget(self._table)
        self._count_label = QLabel("")
        layout.addWidget(self._count_label)

    def _add_actions(self, top) -> None:
        """サブクラスが操作ボタンを追加するためのフック。"""
        pass

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        """サブクラスが行ダブルクリック時の挙動を実装するためのフック。"""
        pass

    def _get_rows(self, session, fiscal_year) -> list[dict]:
        raise NotImplementedError

    def _load(self):
        year = self._year_combo.currentData()
        session = get_session()
        try:
            self._rows = self._get_rows(session, year)
        finally:
            session.close()
        self._table.setRowCount(0)
        for row in self._rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            for col, key in enumerate(self.KEYS):
                self._table.setItem(r, col, QTableWidgetItem(str(row.get(key, ""))))
        self._count_label.setText(f"{len(self._rows)} 件")

    def _export_csv(self):
        if not hasattr(self, '_rows') or not self._rows:
            QMessageBox.information(self, "情報", "データがありません。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "CSV保存", "", "CSV (*.csv)")
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=self.KEYS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._rows)
        QMessageBox.information(self, "完了", f"CSVを保存しました。\n{path}")

    def _export_excel(self):
        if not hasattr(self, '_rows') or not self._rows:
            QMessageBox.information(self, "情報", "データがありません。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Excel保存", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            export_to_excel(self._rows, self.HEADERS, path)
            QMessageBox.information(self, "完了", f"Excelを保存しました。\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", str(e))


class UnpaidReportWidget(_BaseReportWidget):
    HEADERS = ["発行番号", "件名", "年度", "事業所名", "代表者名", "品目",
               "会員番号", "金額", "状態"]
    KEYS = ["doc_number", "project_name", "fiscal_year", "organization_name",
            "representative_name", "description", "member_number", "amount", "status"]

    def _get_rows(self, session, fiscal_year):
        from app.services.report_service import get_unpaid_report
        return get_unpaid_report(session, fiscal_year)

    def _add_actions(self, top):
        self._btn_preview = QPushButton("プレビュー")
        self._btn_preview.setToolTip("選択した請求書のPDFを開いて内容を確認します")
        self._btn_preview.clicked.connect(self._preview_selected)
        top.addWidget(self._btn_preview)

    def _on_cell_double_clicked(self, row, col):
        self._preview_row(row)

    def _preview_selected(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "未選択",
                                    "プレビューする行を選択してください。")
            return
        self._preview_row(row)

    def _preview_row(self, row):
        doc_item = self._table.item(row, 0)
        if doc_item is None:
            return
        doc_number = doc_item.text()
        from sqlalchemy.orm import joinedload
        session = get_session()
        try:
            iss = (session.query(Issuance)
                   .options(joinedload(Issuance.lines))
                   .filter_by(doc_number=doc_number)
                   .first())
            if not iss:
                QMessageBox.critical(self, "エラー", "発行データが見つかりません。")
                return
            from app.utils.pdf_helpers import generate_and_open
            generate_and_open(iss, session)
        except Exception as e:
            QMessageBox.critical(self, "プレビューエラー", str(e))
        finally:
            session.close()


class PaymentReportWidget(_BaseReportWidget):
    HEADERS = ["入金日", "発行番号", "件名", "年度", "宛先", "但し書き",
               "入金額", "入金方法", "担当者"]
    KEYS = ["payment_date", "doc_number", "project_name", "fiscal_year",
            "organization", "description", "amount", "payment_method", "staff_name"]

    def _get_rows(self, session, fiscal_year):
        from app.services.report_service import get_payment_report
        return get_payment_report(session, fiscal_year)


class ProjectSummaryWidget(_BaseReportWidget):
    HEADERS = ["年度", "件名", "全件", "発行済", "支払済", "未発行", "総額", "入金額"]
    KEYS = ["fiscal_year", "project_name", "total", "issued",
            "paid", "pending", "total_amount", "paid_amount"]

    def _get_rows(self, session, fiscal_year):
        from app.services.report_service import get_project_summary
        return get_project_summary(session, fiscal_year)
