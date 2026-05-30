# app/ui/member_import.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QHeaderView
)
from app.database.connection import get_session
from app.services.member_service import create_member
from app.utils.excel_utils import parse_tsv_text, parse_excel_file, MEMBER_COLUMNS

HEADERS = ["会員番号", "事業所名", "フリガナ", "代表者名", "代表者フリガナ",
           "郵便番号", "住所", "電話", "メール"]


class MemberImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("会員インポート")
        self.resize(800, 600)
        self._rows: list[dict] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Excelからコピーして下の欄に貼り付けるか、Excelファイルを選択してください。\n"
            "列順：会員番号 / 事業所名 / フリガナ / 代表者名 / 代表者フリガナ / 郵便番号 / 住所 / 電話 / メール"
        ))

        self._paste_area = QTextEdit()
        self._paste_area.setPlaceholderText("ここにExcelの内容を貼り付け（Ctrl+V）")
        self._paste_area.setFixedHeight(100)
        layout.addWidget(self._paste_area)

        btn_row1 = QHBoxLayout()
        btn_parse = QPushButton("貼り付け内容を解析")
        btn_parse.clicked.connect(self._parse_paste)
        btn_file = QPushButton("Excelファイルを選択")
        btn_file.clicked.connect(self._open_file)
        btn_row1.addWidget(btn_parse)
        btn_row1.addWidget(btn_file)
        btn_row1.addStretch()
        layout.addLayout(btn_row1)

        self._table = QTableWidget(0, len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        btn_row2 = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        self._btn_import = QPushButton("インポート実行")
        self._btn_import.setEnabled(False)
        self._btn_import.clicked.connect(self._import)
        btn_row2.addWidget(btn_cancel)
        btn_row2.addStretch()
        btn_row2.addWidget(self._btn_import)
        layout.addLayout(btn_row2)

    def _show_rows(self, rows: list[dict]):
        self._rows = rows
        self._table.setRowCount(0)
        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            for c, col in enumerate(MEMBER_COLUMNS):
                self._table.setItem(r, c, QTableWidgetItem(row.get(col, "")))
        self._status_label.setText(f"{len(rows)} 件を読み込みました")
        self._btn_import.setEnabled(len(rows) > 0)

    def _parse_paste(self):
        text = self._paste_area.toPlainText()
        rows = parse_tsv_text(text)
        if not rows:
            QMessageBox.warning(self, "解析エラー", "データが見つかりませんでした。")
            return
        self._show_rows(rows)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excelファイルを選択", "", "Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            rows = parse_excel_file(path)
            self._show_rows(rows)
        except Exception as e:
            QMessageBox.critical(self, "読込エラー", str(e))

    def _import(self):
        session = get_session()
        imported = 0
        errors = []
        try:
            for row in self._rows:
                try:
                    create_member(session, **row)
                    imported += 1
                except Exception as e:
                    errors.append(f"{row.get('organization_name', '?')}: {e}")
        finally:
            session.close()
        msg = f"{imported} 件をインポートしました。"
        if errors:
            msg += f"\n失敗 {len(errors)} 件：\n" + "\n".join(errors[:5])
        QMessageBox.information(self, "インポート完了", msg)
        self.accept()
