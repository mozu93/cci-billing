# app/ui/issuance_from_project.py
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QComboBox, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from app.database.connection import get_session
from app.services.project_service import (
    get_projects, get_project_members, get_project_templates
)
from app.services.issuance_service import create_issuance_for_member, mark_as_issued
from app.utils import current_user

COL_CHK = 0
COL_ORG = 1
COL_REP = 2
COL_STA = 3
COL_NUM = 4


class _CheckableTable(QTableWidget):
    """チェックボックス列の Shift+クリック範囲選択に対応したテーブル。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_checked_row: int = -1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self.indexAt(event.pos())
            if idx.isValid() and idx.column() == COL_CHK:
                item = self.item(idx.row(), COL_CHK)
                if item and (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                    if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                            and self._last_checked_row >= 0):
                        # クリック後の状態＝現在の逆
                        new_state = (Qt.CheckState.Unchecked
                                     if item.checkState() == Qt.CheckState.Checked
                                     else Qt.CheckState.Checked)
                        r1 = min(self._last_checked_row, idx.row())
                        r2 = max(self._last_checked_row, idx.row())
                        self.blockSignals(True)
                        for r in range(r1, r2 + 1):
                            it = self.item(r, COL_CHK)
                            if it:
                                it.setCheckState(new_state)
                        self.blockSignals(False)
                        self._last_checked_row = idx.row()
                        return  # super() を呼ばない（二重トグル防止）
                    else:
                        self._last_checked_row = idx.row()
        super().mousePressEvent(event)


class IssuanceFromProjectWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self._load_projects()

    def _build(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("名簿："))
        self._proj_combo = QComboBox()
        self._proj_combo.setMinimumWidth(300)
        self._proj_combo.currentIndexChanged.connect(self._on_project_changed)
        top.addWidget(self._proj_combo)
        top.addWidget(QLabel("表示："))
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["未発行のみ", "すべて"])
        self._filter_combo.currentIndexChanged.connect(self._load_members)
        top.addWidget(self._filter_combo)
        top.addWidget(QLabel("書類種別："))
        self._doctype_combo = QComboBox()
        self._doctype_combo.addItem("請求書", "invoice")
        self._doctype_combo.addItem("領収書", "receipt")
        top.addWidget(self._doctype_combo)
        top.addStretch()
        layout.addLayout(top)

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("事業所名・代表者名で絞り込み")
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._load_members)
        self._search.textChanged.connect(lambda: self._timer.start(300))
        search_row.addWidget(QLabel("検索："))
        search_row.addWidget(self._search)
        layout.addLayout(search_row)

        self._table = _CheckableTable(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["", "事業所名", "代表者名", "ステータス", "発行番号"])

        # 列0ヘッダーにチェックボックスを設定（クリックで全選択/全解除）
        hdr_item = QTableWidgetItem()
        hdr_item.setCheckState(Qt.CheckState.Unchecked)
        self._table.setHorizontalHeaderItem(COL_CHK, hdr_item)
        self._table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

        self._table.setColumnWidth(COL_CHK, 30)
        self._table.horizontalHeader().setSectionResizeMode(
            COL_CHK, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(
            COL_ORG, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_issue = QPushButton("選択した行を発行")
        btn_issue.clicked.connect(self._issue_checked)
        btn_issue_all = QPushButton("全員まとめて発行")
        btn_issue_all.clicked.connect(self._issue_all)
        self._delivery_combo = QComboBox()
        self._delivery_combo.addItems(["窓口手渡し", "郵送", "メール送付", "その他"])
        btn_row.addWidget(btn_issue)
        btn_row.addWidget(btn_issue_all)
        btn_row.addWidget(QLabel("配付方法："))
        btn_row.addWidget(self._delivery_combo)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

    # ── ヘッダークリック：全選択 / 全解除 ─────────────────────────

    def _on_header_clicked(self, col: int):
        if col != COL_CHK:
            return
        hdr = self._table.horizontalHeaderItem(COL_CHK)
        if hdr is None:
            return
        new_state = (Qt.CheckState.Unchecked
                     if hdr.checkState() == Qt.CheckState.Checked
                     else Qt.CheckState.Checked)
        hdr.setCheckState(new_state)
        self._table.blockSignals(True)
        for r in range(self._table.rowCount()):
            it = self._table.item(r, COL_CHK)
            if it:
                it.setCheckState(new_state)
        self._table.blockSignals(False)

    # ── プロジェクト読み込み ───────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._load_projects()

    def _load_projects(self):
        session = get_session()
        try:
            projects = get_projects(session, status="active")
        finally:
            session.close()
        current_id = self._proj_combo.currentData()
        self._proj_combo.blockSignals(True)
        self._proj_combo.clear()
        for p in projects:
            self._proj_combo.addItem(p.name, p.id)
        if current_id is not None:
            for i in range(self._proj_combo.count()):
                if self._proj_combo.itemData(i) == current_id:
                    self._proj_combo.setCurrentIndex(i)
                    break
        self._proj_combo.blockSignals(False)
        self._on_project_changed()

    def _on_project_changed(self):
        project_id = self._proj_combo.currentData()
        if project_id is not None:
            session = get_session()
            try:
                doc_type = self._get_doc_type(session, project_id)
            finally:
                session.close()
            for i in range(self._doctype_combo.count()):
                if self._doctype_combo.itemData(i) == doc_type:
                    self._doctype_combo.setCurrentIndex(i)
                    break
        self._load_members()

    # ── メンバー一覧読み込み ──────────────────────────────────────

    def _load_members(self):
        project_id = self._proj_combo.currentData()
        if project_id is None:
            self._table.setRowCount(0)
            return
        query = self._search.text().strip().lower()
        show_all = self._filter_combo.currentIndex() == 1
        session = get_session()
        try:
            pms = get_project_members(session, project_id)
            from app.database.models import Issuance
            pm_data = []
            for pm in pms:
                iss = (session.query(Issuance)
                       .filter_by(project_member_id=pm.id)
                       .order_by(Issuance.created_at.desc())
                       .first())
                status = iss.status if iss else "未準備"
                doc_number = iss.doc_number if iss else ""
                issuance_id = iss.id if iss else None
                if not show_all and status in ("発行済み", "支払済み"):
                    continue
                if query:
                    targets = [
                        pm.organization_name or "",
                        pm.representative_name or "",
                        pm.organization_kana or "",
                    ]
                    if not any(query in t.lower() for t in targets):
                        continue
                pm_data.append((pm.id, pm, status, doc_number, issuance_id))
        finally:
            session.close()

        # テーブル再構築：チェック状態・範囲選択をリセット
        self._table._last_checked_row = -1
        hdr = self._table.horizontalHeaderItem(COL_CHK)
        if hdr:
            hdr.setCheckState(Qt.CheckState.Unchecked)

        self._table.setRowCount(0)
        for pm_id, pm, status, doc_number, issuance_id in pm_data:
            row = self._table.rowCount()
            self._table.insertRow(row)

            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            chk_item.setCheckState(Qt.CheckState.Unchecked)
            self._table.setItem(row, COL_CHK, chk_item)

            for col_offset, val in enumerate([
                pm.organization_name or "",
                pm.representative_name or "",
                status, doc_number
            ]):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, (pm_id, issuance_id))
                self._table.setItem(row, col_offset + 1, item)

        self._status_label.setText(f"{len(pm_data)} 件表示")

    # ── チェック済み行の取得 ──────────────────────────────────────

    def _checked_rows(self) -> list[tuple[int, int | None]]:
        result = []
        for r in range(self._table.rowCount()):
            chk = self._table.item(r, COL_CHK)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                data_item = self._table.item(r, COL_ORG)
                if data_item:
                    result.append(data_item.data(Qt.ItemDataRole.UserRole))
        return result

    def _get_doc_type(self, session, project_id: int) -> str:
        pts = get_project_templates(session, project_id)
        for pt in pts:
            if pt.item_template.doc_type == "receipt":
                return "receipt"
        return "invoice"

    # ── 発行処理 ──────────────────────────────────────────────────

    def _issue_checked(self):
        """チェックされた行を発行する。"""
        targets = self._checked_rows()
        if not targets:
            QMessageBox.information(self, "未選択",
                                    "発行する行のチェックボックスにチェックを入れてください。")
            return
        project_id = self._proj_combo.currentData()
        doc_type = self._doctype_combo.currentData()
        delivery = self._delivery_combo.currentText()

        session = get_session()
        errors = []
        issued_ids = []
        try:
            from app.database.models import ProjectMember, Issuance
            from app.utils.pdf_helpers import generate_and_open
            for pm_id, issuance_id in targets:
                try:
                    pm = session.get(ProjectMember, pm_id)
                    if issuance_id is None:
                        today = date.today()
                        iss = create_issuance_for_member(
                            session, project_id=project_id,
                            project_member_id=pm_id,
                            recipient_organization=pm.organization_name,
                            recipient_name=pm.representative_name,
                            doc_type=doc_type,
                            fiscal_year=today.year, month=today.month,
                        )
                        issuance_id = iss.id

                    iss = session.get(Issuance, issuance_id)
                    if iss is None:
                        continue
                    if iss.status != "発行済み":
                        mark_as_issued(session, issuance_id,
                                       staff_id=current_user.get_id(),
                                       staff_name=current_user.get_name(),
                                       delivery_method=delivery)
                        iss = session.get(Issuance, issuance_id)
                    issued_ids.append((iss, session))
                except Exception as e:
                    errors.append(str(e))

            for iss, sess in issued_ids:
                try:
                    generate_and_open(iss, sess)
                except Exception as e:
                    errors.append(str(e))

        finally:
            session.close()

        if errors:
            QMessageBox.critical(self, "PDF生成エラー", "\n".join(errors))
        self._load_members()

    def _issue_all(self):
        """全員まとめて発行ボタン：名簿全員ぶんを一括採番・発行・PDF生成する。"""
        project_id = self._proj_combo.currentData()
        if project_id is None:
            return
        doc_type = self._doctype_combo.currentData()
        label = self._doctype_combo.currentText()
        ans = QMessageBox.question(
            self, "確認",
            f"名簿全員ぶんを{label}で発行します。よろしいですか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        session = get_session()
        try:
            from app.utils.pdf_helpers import get_company_and_bank, get_pdf_output_dir
            from app.services.pdf.batch_pdf import generate_batch_pdf
            company, bank = get_company_and_bank(session)
            if not company or not company.name:
                QMessageBox.warning(self, "エラー",
                                    "設定→発行元情報に名称を登録してください。")
                return
            output_dir = get_pdf_output_dir()
            paths = generate_batch_pdf(
                session, project_id, company, output_dir, bank,
                doc_type=doc_type,
            )
            QMessageBox.information(
                self, "完了",
                f"{len(paths)} 件のPDFを生成しました。\n保存先：{output_dir}",
            )
        except Exception as e:
            QMessageBox.critical(self, "エラー", str(e))
        finally:
            session.close()
        self._load_members()
