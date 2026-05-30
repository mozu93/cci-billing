# app/services/backup_service.py
import os
import shutil
from datetime import datetime
from app.utils.app_config import get_db_url, get_config


def get_db_path() -> str | None:
    url = get_db_url()
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "")
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        return path
    return None


def create_backup(db_path: str | None = None,
                  backup_dir: str | None = None) -> str:
    if db_path is None:
        db_path = get_db_path()
    if not db_path or not os.path.exists(db_path):
        raise FileNotFoundError(f"DBファイルが見つかりません: {db_path}")

    if backup_dir is None:
        config = get_config()
        backup_dir = config.get("backup_dir", "")
        if not backup_dir:
            backup_dir = os.path.join(os.path.expanduser("~"), "cci-billing", "backup")

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"cci_billing_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def list_backups(backup_dir: str | None = None) -> list[dict]:
    if backup_dir is None:
        config = get_config()
        backup_dir = config.get("backup_dir", "")
        if not backup_dir:
            backup_dir = os.path.join(os.path.expanduser("~"), "cci-billing", "backup")

    if not os.path.exists(backup_dir):
        return []

    backups = []
    for fname in os.listdir(backup_dir):
        if fname.endswith(".db"):
            fpath = os.path.join(backup_dir, fname)
            stat = os.stat(fpath)
            backups.append({
                "name":       fname,
                "path":       fpath,
                "size":       stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y/%m/%d %H:%M"),
            })
    return sorted(backups, key=lambda x: x["created_at"], reverse=True)


def restore_backup(backup_path: str, db_path: str | None = None) -> None:
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"バックアップファイルが見つかりません: {backup_path}")
    if db_path is None:
        db_path = get_db_path()
    if not db_path:
        raise ValueError("復元先DBパスを特定できません（PostgreSQL構成では手動対応が必要です）。")
    shutil.copy2(backup_path, db_path)
