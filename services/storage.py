from __future__ import annotations

import json
from pathlib import Path

from models.board import Board
from models.workspace import Workspace


class StorageService:
    """Zapis i odczyt lokalnych workspace/tablic Kanban z plików JSON."""

    @staticmethod
    def save_board(board: Board, file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(board.to_dict(), file, ensure_ascii=False, indent=2)

    @staticmethod
    def load_board(file_path: str | Path) -> Board:
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return Board.from_dict(data)

    @staticmethod
    def save_workspace(workspace: Workspace, file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(workspace.to_dict(), file, ensure_ascii=False, indent=2)

    @staticmethod
    def load_workspace(file_path: str | Path) -> Workspace:
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return Workspace.from_dict(data)
