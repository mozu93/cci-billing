# app/ui/issuance_counter.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QSpinBox, QComboBox, QLabel, QPushButton,
    QMessageBox, QFrame, QScrollArea, QStyleFactory, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator
from app.database.connection import get_session
from app.services.category_service import get_active_categories
from app.services.item_template_service import get_all_active_templates
from app.services.issuance_service import create_direct_issuance, update_direct_issuance
from app.utils import current_user

# 列幅・行高（px）
W_CAT   = 150
W_PRICE = 90
W_QTY   = 80
W_SUB   = 90
W_DEL   = 40
ROW_H   = 48
FIELD_H = 26

_SS_FIELD = (
    "QComboBox, QLineEdit, QSpinBox {"
    " border: 1px solid #b5b5b5; border-radius: 3px;"
    " padding: 1px 4px; background: white; }"
)


class _LineRow(QFrame):
    """発行項目1行（業務名／項目／単価／数量／小計／削除）"""

    def __init__(self, panel: "IssuanceCounterWidget"):
        super().__init__()
        self.panel = panel
        self.setFixedHeight(ROW_H)
        self.setObjectName("LineRow")
        self.setStyleSheet(
            "#LineRow { border-bottom: 1px solid #e2e2e2; background: white; }")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(6)

        style = panel._cell_style

        # 業務名
        self.cat_combo = QComboBox()
        self.cat_combo.setFixedWidth(W_CAT)
        self.cat_combo.setFixedHeight(FIELD_H)
        # 項目
        self.tmpl_combo = QComboBox()
        self.tmpl_combo.setFixedHeight(FIELD_H)
        self.tmpl_combo.addItem("（項目を選択）", None)
        # 単価
        self.price_edit = QLineEdit("0")
        self.price_edit.setFixedWidth(W_PRICE)
        self.price_edit.setFixedHeight(FIELD_H)
        self.price_edit.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.price_edit.setValidator(QIntValidator(0, 99_999_999, self))
        # 数量
        self.qty_spin = QSpinBox()
        self.qty_spin.setFixedWidth(W_QTY)
        self.qty_spin.setFixedHeight(FIELD_H)
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setValue(1)
        # 小計
        self.sub_label = QLabel("¥0")
        self.sub_label.setFixedWidth(W_SUB)
        self.sub_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # 削除
        self.btn_del = QPushButton("✕")
        self.btn_del.setFixedSize(W_DEL, FIELD_H)
        self.btn_del.setStyleSheet(
            "QPushButton { color: #cc4444; border: none;"
            " background: transparent; font-weight: bold; }"
            "QPushButton:hover { color: #ff0000; }")

        for w in (self.cat_combo, self.tmpl_combo, self.price_edit, self.qty_spin):
            if style:
                w.setStyle(style)
            w.setStyleSheet(_SS_FIELD)

        lay.addWidget(self.cat_combo)
        lay.addWidget(self.tmpl_combo, 1)
        lay.addWidget(self.price_edit)
        lay.addWidget(self.qty_spin)
        lay.addWidget(self.sub_label)
        lay.addWidget(self.btn_del)

        # シグナル
        self.cat_combo.currentIndexChanged.connect(
            lambda: self.panel._on_cat_changed(self))
        self.tmpl_combo.currentIndexChanged.connect(
            lambda: self.panel._on_tmpl_changed(self))
        self.price_edit.textChanged.connect(self.panel._update_total)
        self.qty_spin.valueChanged.connect(self.panel._update_total)
        self.btn_del.clicked.connect(lambda: self.panel._remove_row(self))

    def price(self) -> int:
        try:
            return int(self.price_edit.text())
        except (ValueError, TypeError):
            return 0


class IssuanceCounterWidget(QWidget):
    edit_completed = pyqtSignal()

    def __init__(self, doc_type: str = "receipt", edit_issuance_id: int | None = None):
        super().__init__()
        self._doc_type_str = doc_type
        self._edit_issuance_id = edit_issuance_id
        self._edit_loaded = False
        self._categories = []
        self._templates  = []
        self._cat_name_by_id: dict[int, str] = {}
        self._rows: list[_LineRow] = []
        self._cell_style = QStyleFactory.create("Fusion")
        self._build()

    def showEvent(self, event):
        super().showEvent(event)
        self._reload_master()
        if self._edit_issuance_id is not None and not self._edit_loaded:
            self._load_edit_data()
            self._edit_loaded = True

    # ── マスタ読み込み ───────────────────────────────────

    def _reload_master(self):
        session = get_session()
        try:
            self._categories = get_active_categories(session)
            self._templates  = get_all_active_templates(session)
        finally:
            session.close()
        self._cat_name_by_id = {c.id: c.name for c in self._categories}
        for row in self._rows:
            self._refresh_cat_combo(row.cat_combo)
            self._refresh_tmpl_combo(row)

    def _load_edit_data(self):
        """編集モード：既存の Issuance からフォームを復元する。"""
        from app.database.connection import get_session
        from app.database.models import Issuance
        from sqlalchemy.orm import joinedload
        session = get_session()
        try:
            iss = (session.query(Issuance)
                   .options(joinedload(Issuance.lines))
                   .filter_by(id=self._edit_issuance_id)
                   .first())
            if iss is None:
                return
            self._org_name.setText(iss.recipient_organization or "")
            self._rep_name.setText(iss.recipient_name or "")
            idx = self._delivery.findText(iss.delivery_method or "")
            if idx >= 0:
                self._delivery.setCurrentIndex(idx)
            for line in iss.lines:
                self._add_row()
                self._populate_row_from_line(self._rows[-1], line)
        finally:
            session.close()
        self._update_total()

    def _populate_row_from_line(self, row: "_LineRow", line) -> None:
        """IssuanceLine の内容を行ウィジェットに復元する。"""
        tmpl = next((t for t in self._templates if t.id == line.item_template_id), None)
        cat_id = tmpl.category_id if tmpl else None

        # カテゴリ選択（シグナル不要）
        row.cat_combo.blockSignals(True)
        for i in range(row.cat_combo.count()):
            if row.cat_combo.itemData(i) == cat_id:
                row.cat_combo.setCurrentIndex(i)
                break
        row.cat_combo.blockSignals(False)

        # テンプレートコンボを再構築してから選択
        self._refresh_tmpl_combo(row)
        row.tmpl_combo.blockSignals(True)
        for i in range(row.tmpl_combo.count()):
            if row.tmpl_combo.itemData(i) == line.item_template_id:
                row.tmpl_combo.setCurrentIndex(i)
                break
        row.tmpl_combo.blockSignals(False)

        row.price_edit.blockSignals(True)
        row.price_edit.setText(str(int(line.unit_price)))
        row.price_edit.blockSignals(False)

        row.qty_spin.blockSignals(True)
        row.qty_spin.setValue(int(line.quantity))
        row.qty_spin.blockSignals(False)

    def _tmpls_for_cat(self, cat_id) -> list:
        if cat_id is None:
            return self._templates
        return [t for t in self._templates if t.category_id == cat_id]

    def _add_template_master(self):
        """その場で新規テンプレートをマスタ登録し、選択肢に反映する。"""
        from PyQt6.QtWidgets import QDialog
        from app.ui.item_template_management import ItemTemplateDialog
        dlg = ItemTemplateDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_master()

    def _add_category_master(self):
        """その場で新規業務名（カテゴリ）を登録し、選択肢に反映する。"""
        from PyQt6.QtWidgets import QDialog
        from app.ui.category_management import CategoryEditDialog
        from app.services.category_service import create_category
        dlg = CategoryEditDialog(self, title="業務名の登録")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, sort_order = dlg.values()
        if not name:
            return
        session = get_session()
        try:
            create_category(session, name, sort_order)
        finally:
            session.close()
        self._reload_master()

    # ── UI構築 ───────────────────────────────────────────

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # ── 上部2カラム ──────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        grp_dest = QGroupBox("宛先")
        form = QFormLayout(grp_dest)
        form.setContentsMargins(10, 8, 10, 8)
        form.setSpacing(8)
        self._org_name = QLineEdit()
        self._org_name.setPlaceholderText("事業所名（任意）")
        self._rep_name = QLineEdit()
        self._rep_name.setPlaceholderText("代表者名・個人名（どちらか必須）")
        form.addRow("事業所名",     self._org_name)
        form.addRow("担当者・個人名", self._rep_name)
        top_row.addWidget(grp_dest, 6)

        grp_opts = QGroupBox("発行設定")
        opts_form = QFormLayout(grp_opts)
        opts_form.setContentsMargins(10, 8, 10, 8)
        opts_form.setSpacing(8)
        self._delivery = QComboBox()
        self._delivery.addItems(["窓口手渡し", "郵送", "メール送付", "その他"])
        opts_form.addRow("配付方法", self._delivery)
        fmt_text = "A4縦" if self._doc_type_str == "invoice" else "A5縦"
        fmt_note = QLabel(f"印刷形式：{fmt_text}（固定）")
        fmt_note.setStyleSheet("color: #666; font-size: 11px;")
        opts_form.addRow("", fmt_note)
        top_row.addWidget(grp_opts, 4)

        layout.addLayout(top_row)

        # ── 発行項目 ─────────────────────────────────────
        grp_lines = QGroupBox("発行項目")
        lines_layout = QVBoxLayout(grp_lines)
        lines_layout.setContentsMargins(8, 8, 8, 8)
        lines_layout.setSpacing(0)

        lines_layout.addWidget(self._make_header())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(140)

        self._rows_container = QWidget()
        self._rows_container.setStyleSheet("background: white;")
        self._rows_vbox = QVBoxLayout(self._rows_container)
        self._rows_vbox.setContentsMargins(0, 0, 0, 2)
        self._rows_vbox.setSpacing(0)
        self._rows_vbox.addStretch()
        scroll.setWidget(self._rows_container)
        lines_layout.addWidget(scroll)

        add_btn_row = QHBoxLayout()
        btn_add = QPushButton("＋ 項目を追加")
        btn_add.setFixedHeight(32)
        btn_add.clicked.connect(self._add_row)
        add_btn_row.addWidget(btn_add)
        btn_new_cat = QPushButton("＋ 新規業務登録")
        btn_new_cat.setFixedHeight(32)
        btn_new_cat.clicked.connect(self._add_category_master)
        add_btn_row.addWidget(btn_new_cat)
        btn_new_tmpl = QPushButton("＋ 新規テンプレート…")
        btn_new_tmpl.setFixedHeight(32)
        btn_new_tmpl.clicked.connect(self._add_template_master)
        add_btn_row.addWidget(btn_new_tmpl)
        lines_layout.addLayout(add_btn_row)
        layout.addWidget(grp_lines)

        # ── 合計 + 発行ボタン ────────────────────────────
        self._total_label = QLabel("合計：¥0")
        self._total_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #1D4ED8; padding: 6px 2px;")
        layout.addWidget(self._total_label)

        _btn_lbl = "修正して再発行" if self._edit_issuance_id else "発行する"
        self._btn_issue = QPushButton(_btn_lbl)
        self._btn_issue.setFixedHeight(44)
        self._btn_issue.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
            "background: #1D4ED8; color: white; border-radius: 6px;")
        self._btn_issue.clicked.connect(self._issue)
        layout.addWidget(self._btn_issue)
        layout.addStretch()

        if not self._edit_issuance_id:
            self._add_row()

    def _make_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setFixedHeight(30)
        hdr.setStyleSheet("background: #eef1f5; border-bottom: 1px solid #d0d0d0;")
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(6)
        specs = [("業務名", W_CAT), ("項目", None), ("単価（円）", W_PRICE),
                 ("数量", W_QTY), ("小計", W_SUB), ("", W_DEL)]
        for text, w in specs:
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; color: #333; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if w is None:
                lay.addWidget(lbl, 1)
            else:
                lbl.setFixedWidth(w)
                lay.addWidget(lbl)
        return hdr

    # ── コンボ更新ヘルパ ─────────────────────────────────

    def _refresh_cat_combo(self, combo: QComboBox):
        cur = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("（業務名を選択）", None)
        for c in self._categories:
            combo.addItem(c.name, c.id)
        if cur is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == cur:
                    combo.setCurrentIndex(i)
                    break
        combo.blockSignals(False)

    def _refresh_tmpl_combo(self, row: _LineRow):
        cat_id     = row.cat_combo.currentData()
        cur_id     = row.tmpl_combo.currentData()
        candidates = self._tmpls_for_cat(cat_id)
        row.tmpl_combo.blockSignals(True)
        row.tmpl_combo.clear()
        row.tmpl_combo.addItem("（項目を選択）", None)
        for t in candidates:
            label = f"{t.name}　¥{int(t.unit_price):,}/{t.unit}"
            # 業務名で絞り込んでいないときは、同名項目を見分けられるよう業務名を併記
            if cat_id is None:
                cname = self._cat_name_by_id.get(t.category_id)
                if cname:
                    label = f"{t.name}（{cname}）　¥{int(t.unit_price):,}/{t.unit}"
            row.tmpl_combo.addItem(label, t.id)
        restored = False
        if cur_id is not None:
            for i in range(row.tmpl_combo.count()):
                if row.tmpl_combo.itemData(i) == cur_id:
                    row.tmpl_combo.setCurrentIndex(i)
                    restored = True
                    break
        if not restored:
            row.tmpl_combo.setCurrentIndex(0)
        row.tmpl_combo.blockSignals(False)

    # ── 行操作 ──────────────────────────────────────────

    def _add_row(self):
        row = _LineRow(self)
        self._refresh_cat_combo(row.cat_combo)
        # stretch の直前に挿入
        self._rows_vbox.insertWidget(self._rows_vbox.count() - 1, row)
        self._rows.append(row)
        self._update_total()

    def _remove_row(self, row: _LineRow):
        if row not in self._rows:
            return
        self._rows.remove(row)
        self._rows_vbox.removeWidget(row)
        row.setParent(None)
        row.deleteLater()
        self._update_total()

    # ── シグナルハンドラ ─────────────────────────────────

    def _on_cat_changed(self, row: _LineRow):
        self._refresh_tmpl_combo(row)
        self._update_total()

    def _on_tmpl_changed(self, row: _LineRow):
        self._apply_template_to_row(row)

    def _apply_template_to_row(self, row: _LineRow):
        tmpl_id = row.tmpl_combo.currentData()
        tmpl = next((t for t in self._templates if t.id == tmpl_id), None)
        row.price_edit.setText(str(int(tmpl.unit_price)) if tmpl else "0")
        self._update_total()

    def _update_total(self):
        total = 0
        for row in self._rows:
            sub = row.price() * row.qty_spin.value()
            total += sub
            row.sub_label.setText(f"¥{sub:,}")
        self._total_label.setText(f"合計：¥{total:,}")

    # ── 発行 ─────────────────────────────────────────────

    def _derive_project_name(self) -> str:
        """選択された項目（テンプレート）の業務名から集計先プロジェクト名を決める。

        業務名コンボの選択ではなく、項目自身が属する業務名を使うので、
        業務名を選ばずに項目だけ選んでも正しい業務名に集計される。
        """
        seen: dict[str, bool] = {}
        for row in self._rows:
            tmpl_id = row.tmpl_combo.currentData()
            tmpl = next((t for t in self._templates if t.id == tmpl_id), None)
            if tmpl is None:
                continue
            name = self._cat_name_by_id.get(tmpl.category_id)
            if name and name not in seen:
                seen[name] = True
        return "・".join(seen.keys()) if seen else "直接発行"

    def _issue(self):
        org = self._org_name.text().strip()
        rep = self._rep_name.text().strip()
        if not org and not rep:
            QMessageBox.warning(self, "入力エラー",
                                "事業所名または担当者・個人名を入力してください。")
            return
        if not self._templates:
            QMessageBox.warning(self, "テンプレート未登録",
                                "請求項目テンプレートが登録されていません。\n"
                                "設定 → 請求項目テンプレートから登録してください。")
            return
        if not self._rows:
            QMessageBox.warning(self, "入力エラー", "項目を1つ以上追加してください。")
            return

        lines_data = []
        for row in self._rows:
            tmpl_id = row.tmpl_combo.currentData()
            tmpl    = next((t for t in self._templates if t.id == tmpl_id), None)
            if tmpl is None:
                continue
            price = row.price() or int(tmpl.unit_price)
            lines_data.append({
                "item_template_id": tmpl.id,
                "item_name":        tmpl.name,
                "quantity":         row.qty_spin.value(),
                "unit":             tmpl.unit,
                "unit_price":       price,
                "tax_rate":         tmpl.tax_rate,
            })

        if not lines_data:
            QMessageBox.warning(self, "エラー",
                                "項目が選択されていません。\n"
                                "各行で項目を選択してください。")
            return

        doc_type = self._doc_type_str
        fmt      = "a4" if doc_type == "invoice" else "a5"
        session  = get_session()
        try:
            if self._edit_issuance_id is not None:
                iss = update_direct_issuance(
                    session,
                    issuance_id            = self._edit_issuance_id,
                    lines_data             = lines_data,
                    recipient_organization = org,
                    recipient_name         = rep,
                    delivery_method        = self._delivery.currentText(),
                    staff_id               = current_user.get_id(),
                    staff_name             = current_user.get_name(),
                )
            else:
                project_name = self._derive_project_name()
                today = date.today()
                iss = create_direct_issuance(
                    session,
                    lines_data             = lines_data,
                    recipient_organization = org,
                    recipient_name         = rep,
                    doc_type               = doc_type,
                    fiscal_year            = today.year,
                    month                  = today.month,
                    staff_id               = current_user.get_id(),
                    staff_name             = current_user.get_name(),
                    delivery_method        = self._delivery.currentText(),
                    project_name           = project_name,
                )
            from app.utils.pdf_helpers import generate_and_open
            due_date = None
            if doc_type == "invoice":
                from app.ui.invoice_options_dialog import InvoiceOptionsDialog
                opts = InvoiceOptionsDialog(issued_at=iss.issued_at, parent=self)
                if opts.exec() != QDialog.DialogCode.Accepted:
                    return
                due_date = opts.due_date()
            generate_and_open(iss, session, receipt_fmt=fmt, due_date=due_date)
        except Exception as e:
            QMessageBox.critical(self, "発行エラー", str(e))
            return
        finally:
            session.close()

        if self._edit_issuance_id is not None:
            self.edit_completed.emit()
        else:
            self._org_name.clear()
            self._rep_name.clear()
            for row in list(self._rows):
                self._remove_row(row)
            self._add_row()
            self._update_total()
