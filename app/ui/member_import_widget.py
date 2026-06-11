# app/ui/member_import_widget.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QMessageBox
)


class MemberImportWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._file_path = ""
        self._build()
        self._refresh_count()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        desc = QLabel(
            "CSVファイルから会員データ（約4,000件）を一括登録します。\n"
            "インポートを実行すると既存データは全削除されてから再登録されます。\n\n"
            "対応ヘッダー例：会員番号・事業所名・フリガナ・氏名・氏名フリガナ・"
            "電話番号・メール・郵便番号・住所・住所2"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        file_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText("CSVファイルを選択してください")
        btn_browse = QPushButton("ファイルを選択…")
        btn_browse.clicked.connect(self._browse)
        file_row.addWidget(self._path_edit, 1)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        self._btn_import = QPushButton("インポート（全削除→再登録）")
        self._btn_import.setFixedHeight(36)
        self._btn_import.setEnabled(False)
        self._btn_import.setStyleSheet(
            "QPushButton:enabled { background: #1D4ED8; color: white; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:disabled { background: #ccc; color: #666; border-radius: 4px; }"
        )
        self._btn_import.clicked.connect(self._do_import)
        layout.addWidget(self._btn_import)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #555;")
        layout.addWidget(self._count_label)

        self._result_label = QLabel("")
        layout.addWidget(self._result_label)

        layout.addStretch()

    def _refresh_count(self):
        from app.database.connection import get_session
        from app.services.member_service import count_members
        session = get_session()
        try:
            n = count_members(session)
        finally:
            session.close()
        self._count_label.setText(f"現在の登録件数：{n:,} 件")

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "CSVファイルを選択", "", "CSVファイル (*.csv);;すべてのファイル (*)"
        )
        if path:
            self._file_path = path
            self._path_edit.setText(path)
            self._btn_import.setEnabled(True)
            self._result_label.setText("")

    def _do_import(self):
        if not self._file_path:
            return
        reply = QMessageBox.question(
            self, "確認",
            "既存の会員データをすべて削除してからCSVを再登録します。\nよろしいですか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from app.database.connection import get_session
        from app.services.member_service import import_from_csv
        session = get_session()
        try:
            count = import_from_csv(session, self._file_path)
            self._result_label.setText(f"インポート完了：{count:,} 件を登録しました。")
            self._result_label.setStyleSheet("color: green; font-weight: bold;")
        except Exception as e:
            self._result_label.setText(f"エラー：{e}")
            self._result_label.setStyleSheet("color: red;")
        finally:
            session.close()
        self._refresh_count()
