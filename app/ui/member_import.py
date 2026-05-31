# app/ui/member_import.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QHeaderView, QComboBox, QCheckBox, QGroupBox
)
from app.database.connection import get_session
from app.services.member_service import create_member
from app.utils.excel_utils import (
    MEMBER_COLUMNS, FIELD_LABELS, REQUIRED_ANY,
    parse_tsv_text_raw, parse_excel_file_raw, column_count,
    default_positional_mapping, guess_mapping_from_header, build_member_rows,
)

HEADERS = [FIELD_LABELS[c] for c in MEMBER_COLUMNS]


class MemberImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("会員インポート")
        self.resize(820, 680)
        self._raw_rows: list[list[str]] = []
        self._field_combos: dict[str, QComboBox] = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Excelからコピーして下の欄に貼り付けるか、Excelファイルを選択してください。\n"
            "読み込み後、各項目にどの列を当てるかを選べます（列順がバラバラでも可）。"
        ))

        self._paste_area = QTextEdit()
        self._paste_area.setPlaceholderText("ここにExcelの内容を貼り付け（Ctrl+V）")
        self._paste_area.setFixedHeight(90)
        layout.addWidget(self._paste_area)

        btn_row1 = QHBoxLayout()
        btn_parse = QPushButton("貼り付け内容を読み込む")
        btn_parse.clicked.connect(self._load_paste)
        btn_file = QPushButton("Excelファイルを選択")
        btn_file.clicked.connect(self._open_file)
        btn_row1.addWidget(btn_parse)
        btn_row1.addWidget(btn_file)
        btn_row1.addStretch()
        layout.addLayout(btn_row1)

        # ── 列の割り当て（マッピング）──────────────────────────
        self._map_group = QGroupBox("列の割り当て（取り込み先 ← 元の列）")
        map_layout = QGridLayout(self._map_group)
        self._header_chk = QCheckBox("1行目を見出しとして使う（見出し名から自動割り当て）")
        self._header_chk.stateChanged.connect(self._on_header_toggle)
        map_layout.addWidget(self._header_chk, 0, 0, 1, 4)

        for n, field in enumerate(MEMBER_COLUMNS):
            r = 1 + n // 2
            c = (n % 2) * 2
            label = FIELD_LABELS[field]
            if field in REQUIRED_ANY:
                label += " ※"
            combo = QComboBox()
            combo.currentIndexChanged.connect(self._refresh_preview)
            self._field_combos[field] = combo
            map_layout.addWidget(QLabel(label), r, c)
            map_layout.addWidget(combo, r, c + 1)

        note = QLabel("※「事業所名」「代表者名」のいずれかが必要です。")
        note.setStyleSheet("color: #666; font-size: 11px;")
        map_layout.addWidget(note, 1 + (len(MEMBER_COLUMNS) + 1) // 2, 0, 1, 4)
        self._map_group.setEnabled(False)
        layout.addWidget(self._map_group)

        # ── プレビュー ────────────────────────────────────────
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

    # ── 読み込み ──────────────────────────────────────────────

    def _load_paste(self):
        rows = parse_tsv_text_raw(self._paste_area.toPlainText())
        if not rows:
            QMessageBox.warning(self, "読込エラー", "データが見つかりませんでした。")
            return
        self._set_raw_rows(rows)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excelファイルを選択", "", "Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            rows = parse_excel_file_raw(path)
        except Exception as e:
            QMessageBox.critical(self, "読込エラー", str(e))
            return
        if not rows:
            QMessageBox.warning(self, "読込エラー", "データが見つかりませんでした。")
            return
        self._set_raw_rows(rows)

    def _set_raw_rows(self, rows: list[list[str]]):
        self._raw_rows = rows
        self._map_group.setEnabled(True)
        self._rebuild_mapping_ui()
        self._refresh_preview()

    # ── マッピングUI ──────────────────────────────────────────

    def _rebuild_mapping_ui(self):
        num_cols = column_count(self._raw_rows)
        sample = self._raw_rows[0] if self._raw_rows else []
        has_header = self._header_chk.isChecked()
        if has_header and self._raw_rows:
            guessed = guess_mapping_from_header(self._raw_rows[0])
        else:
            guessed = default_positional_mapping(num_cols)

        for field, combo in self._field_combos.items():
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("（なし）", None)
            for i in range(num_cols):
                val = sample[i] if i < len(sample) else ""
                if len(val) > 12:
                    val = val[:12] + "…"
                combo.addItem(f"列{i + 1}: {val}", i)
            target = guessed.get(field)
            idx = combo.findData(target) if target is not None else 0
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

    def _on_header_toggle(self):
        if self._raw_rows:
            self._rebuild_mapping_ui()
            self._refresh_preview()

    def _current_mapping(self) -> dict[str, int | None]:
        return {field: combo.currentData()
                for field, combo in self._field_combos.items()}

    # ── プレビュー & 取り込み ─────────────────────────────────

    def _mapped_rows(self) -> list[dict]:
        return build_member_rows(
            self._raw_rows, self._current_mapping(),
            has_header=self._header_chk.isChecked())

    def _refresh_preview(self):
        rows = self._mapped_rows()
        self._table.setRowCount(0)
        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            for c, col in enumerate(MEMBER_COLUMNS):
                self._table.setItem(r, c, QTableWidgetItem(row.get(col, "")))
        self._status_label.setText(f"取り込み対象：{len(rows)} 件")
        self._btn_import.setEnabled(len(rows) > 0)

    def _import(self):
        rows = self._mapped_rows()
        session = get_session()
        imported = 0
        errors = []
        try:
            for row in rows:
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
