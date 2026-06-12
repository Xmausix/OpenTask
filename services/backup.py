from __future__ import annotations

from datetime import datetime
from pathlib import Path

from models.workspace import Workspace
from services.storage import StorageService


class BackupService:
    def __init__(self, backup_dir: str | Path = "backups") -> None:
        self.backup_dir = Path(backup_dir)

    def create_backup(self, workspace: Workspace) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.backup_dir / f"workspace_backup_{stamp}.json"
        StorageService.save_workspace(workspace, path)
        return path
