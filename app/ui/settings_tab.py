# app/ui/settings_tab.py
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        inner = QTabWidget()

        from app.ui.company_settings import CompanySettingsWidget
        from app.ui.staff_management import StaffManagementWidget
        from app.ui.category_management import CategoryManagementWidget
        from app.ui.item_template_management import ItemTemplateManagementWidget
        from app.ui.email_settings import EmailSettingsWidget
        from app.ui.backup_settings import BackupSettingsWidget
        from app.ui.operation_log_tab import OperationLogWidget
        from app.ui.member_import_widget import MemberImportWidget
        from app.utils import current_user

        inner.addTab(CompanySettingsWidget(), "発行元情報")
        inner.addTab(StaffManagementWidget(), "スタッフ管理")
        inner.addTab(CategoryManagementWidget(), "業務名")
        inner.addTab(ItemTemplateManagementWidget(), "請求項目テンプレート")
        inner.addTab(MemberImportWidget(), "会員マスタ")
        inner.addTab(EmailSettingsWidget(), "メール設定")
        inner.addTab(BackupSettingsWidget(), "バックアップ")
        inner.addTab(OperationLogWidget(), "操作ログ")

        if current_user.is_admin():
            inner.addTab(_AdminWidget(), "管理者")

        layout.addWidget(inner)


class _AdminWidget(QWidget):
    """管理者専用タブ：データ初期化などの高権限操作を提供する。"""

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)
        root.setSpacing(16)
        root.setContentsMargins(16, 16, 16, 16)

        # ── データ初期化 ─────────────────────────────────────────
        grp = QGroupBox("データ初期化")
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(10)

        desc = QLabel(
            "業務データ（案件・発行書類・入金記録・会員マスタ・操作ログ）を\n"
            "すべて削除します。\n"
            "スタッフアカウント・会社情報・請求項目テンプレート・業務名は保持されます。"
        )
        desc.setStyleSheet("color: #555; font-size: 12px;")
        grp_layout.addWidget(desc)

        btn_row = QHBoxLayout()
        btn_init = QPushButton("データを初期化する")
        btn_init.setStyleSheet(
            "QPushButton { background: #dc2626; color: white; "
            "border: none; padding: 6px 18px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #b91c1c; }"
        )
        btn_init.clicked.connect(self._on_init_clicked)
        btn_row.addWidget(btn_init)
        btn_row.addStretch()
        grp_layout.addLayout(btn_row)

        root.addWidget(grp)

    def _on_init_clicked(self):
        # 1回目の確認
        ans = QMessageBox.warning(
            self,
            "データ初期化の確認",
            "以下のデータをすべて削除します。この操作は取り消せません。\n\n"
            "　・案件（件名・名簿・テンプレート割り当て）\n"
            "　・発行済み書類（請求書・領収書）および明細\n"
            "　・入金記録\n"
            "　・会員マスタ\n"
            "　・操作ログ\n\n"
            "本当に初期化しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        # 2回目の確認（誤操作防止）
        ans2 = QMessageBox.critical(
            self,
            "最終確認",
            "業務データを完全に削除します。\n復元できません。実行しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans2 != QMessageBox.StandardButton.Yes:
            return

        self._do_initialize()

    def _do_initialize(self):
        from app.database.connection import get_session
        from sqlalchemy import text
        session = get_session()
        # 外部キー制約の順序で全行削除（ORM評価を介さず直接SQL）
        tables = [
            "payments",
            "issuance_lines",
            "issuances",
            "project_members",
            "project_templates",
            "projects",
            "members",
            "operation_logs",
        ]
        try:
            for tbl in tables:
                session.execute(text(f"DELETE FROM {tbl}"))
            session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "初期化エラー", f"初期化中にエラーが発生しました。\n{e}")
            return
        finally:
            session.close()

        QMessageBox.information(
            self, "初期化完了",
            "業務データを初期化しました。\nアプリを再起動することを推奨します。"
        )
