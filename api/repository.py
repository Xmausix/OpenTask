from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from uuid import uuid4

from models.activity import ActivityLog
from models.board import Board
from models.card import Card
from models.checklist import ChecklistItem
from models.column import Column
from models.comment import Comment
from models.label import Label
from models.workspace import Workspace
from services.dragdrop import move_card
from services.search import card_matches
from services.storage import StorageService
from services.templates import create_board_from_template


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class WorkspaceRepository:
    """Thread-safe lokalne repozytorium dla REST API.

    API działa lokalnie i domyślnie zapisuje stan do `data/api_workspace.json`.
    Ścieżkę można zmienić zmienną środowiskową `BETTER_TRELLO_API_DATA`.
    """

    def __init__(self, data_file: str | Path | None = None) -> None:
        default_file = Path(__file__).resolve().parents[1] / "data" / "api_workspace.json"
        self.data_file = Path(data_file or os.getenv("BETTER_TRELLO_API_DATA", default_file))
        self.lock = RLock()
        self.workspace = self._load_or_default()

    def _load_or_default(self) -> Workspace:
        if self.data_file.exists():
            try:
                return StorageService.load_workspace(self.data_file)
            except Exception:
                return Workspace.default()
        return Workspace.default()

    def persist(self) -> None:
        StorageService.save_workspace(self.workspace, self.data_file)

    def workspace_dict(self) -> dict:
        with self.lock:
            return self.workspace.to_dict()

    def update_workspace(self, name: str | None = None, active_board_id: str | None = None) -> dict:
        with self.lock:
            if name:
                self.workspace.name = name
            if active_board_id:
                self.get_board(active_board_id)
                self.workspace.active_board_id = active_board_id
            self.persist()
            return self.workspace.to_dict()

    def load_from_json(self, path: str | Path) -> dict:
        with self.lock:
            self.workspace = StorageService.load_workspace(path)
            self.data_file = Path(path)
            self.persist()
            return self.workspace.to_dict()

    def save_to_json(self, path: str | Path | None = None) -> dict:
        with self.lock:
            if path:
                self.data_file = Path(path)
            self.persist()
            return {"path": str(self.data_file)}

    def boards(self, include_archived: bool = False) -> list[dict]:
        with self.lock:
            return [board.to_dict() for board in self.workspace.visible_boards(include_archived=include_archived)]

    def get_board(self, board_id: str) -> Board:
        for board in self.workspace.boards:
            if board.id == board_id:
                return board
        raise NotFoundError(f"Nie znaleziono tablicy: {board_id}")

    def board_dict(self, board_id: str) -> dict:
        with self.lock:
            return self.get_board(board_id).to_dict()

    def create_board(self, name: str, template: str = "Kanban") -> dict:
        with self.lock:
            board = create_board_from_template(name, template)
            self.workspace.add_board(board)
            board.add_activity("api_board_created", name)
            self.persist()
            return board.to_dict()

    def update_board(self, board_id: str, **changes) -> dict:
        with self.lock:
            board = self.get_board(board_id)
            if changes.get("name") is not None:
                board.name = changes["name"]
            if changes.get("favorite") is not None:
                board.favorite = bool(changes["favorite"])
            if changes.get("archived") is not None:
                board.archived = bool(changes["archived"])
            board.add_activity("api_board_updated", board.name)
            self.persist()
            return board.to_dict()

    def delete_board(self, board_id: str, hard: bool = False) -> dict:
        with self.lock:
            board = self.get_board(board_id)
            if hard:
                if len(self.workspace.boards) <= 1:
                    raise ValidationError("Nie można usunąć ostatniej tablicy.")
                self.workspace.boards.remove(board)
                if self.workspace.active_board_id == board_id:
                    self.workspace.active_board_id = self.workspace.boards[0].id
                result = {"deleted": board_id, "hard": True}
            else:
                board.archived = True
                board.add_activity("api_board_archived", board.name)
                result = board.to_dict()
            self.persist()
            return result

    def get_column(self, board: Board, column_id: str) -> Column:
        for column in board.columns:
            if column.id == column_id:
                return column
        raise NotFoundError(f"Nie znaleziono kolumny: {column_id}")

    def create_column(self, board_id: str, name: str, emoji: str = "") -> dict:
        with self.lock:
            board = self.get_board(board_id)
            column = Column(name=name, emoji=emoji)
            board.columns.append(column)
            board.add_activity("api_column_created", name)
            self.persist()
            return column.to_dict()

    def find_card(self, card_id: str) -> tuple[Board, Column, Card]:
        for board in self.workspace.boards:
            for column in board.columns:
                for card in column.cards:
                    if card.id == card_id:
                        return board, column, card
        raise NotFoundError(f"Nie znaleziono karty: {card_id}")

    def cards(self, board_id: str, query: str = "", include_archived: bool = False) -> list[dict]:
        with self.lock:
            board = self.get_board(board_id)
            result: list[dict] = []
            for column in board.columns:
                for card in column.cards:
                    if card.archived and not include_archived:
                        continue
                    if query and not card_matches(card, query=query):
                        continue
                    item = card.to_dict()
                    item["column_id"] = column.id
                    item["column_name"] = column.name
                    result.append(item)
            return result

    def create_card(self, board_id: str, payload: dict) -> dict:
        with self.lock:
            board = self.get_board(board_id)
            column = self.get_column(board, payload["column_id"])
            card = Card(
                title=payload["title"],
                description=payload.get("description", ""),
                priority=payload.get("priority", "medium"),
                labels=[Label(name=item.get("name", ""), color=item.get("color", "#3b82f6")) for item in payload.get("labels", [])],
                due_date=payload.get("due_date"),
                members=list(payload.get("members", [])),
                checklist=[ChecklistItem(text=item.get("text", ""), done=bool(item.get("done", False))) for item in payload.get("checklist", [])],
                cover_color=payload.get("cover_color", ""),
                template=payload.get("template", ""),
            )
            column.cards.append(card)
            board.add_activity("api_card_created", card.title)
            self.persist()
            return card.to_dict()

    def update_card(self, card_id: str, changes: dict) -> dict:
        with self.lock:
            board, _column, card = self.find_card(card_id)
            for key in ["title", "description", "priority", "due_date", "cover_color", "archived", "dependencies"]:
                if key in changes and changes[key] is not None:
                    setattr(card, key, changes[key])
            if changes.get("members") is not None:
                card.members = list(changes["members"])
            card.touch()
            board.add_activity("api_card_updated", card.title)
            self.persist()
            return card.to_dict()

    def move_card_to_column(self, card_id: str, target_column_id: str, target_index: int | None = None) -> dict:
        with self.lock:
            board, source, card = self.find_card(card_id)
            target = self.get_column(board, target_column_id)
            if source is target:
                if target_index is not None and 0 <= target_index < len(source.cards):
                    source.cards.remove(card)
                    source.cards.insert(target_index, card)
            else:
                move_card(card, source, target, target_index=target_index)
            card.touch()
            board.add_activity("api_card_moved", f"{card.title}: {source.name} → {target.name}")
            self.persist()
            return card.to_dict()

    def add_comment(self, card_id: str, text: str, author: str = "API User") -> dict:
        with self.lock:
            board, _column, card = self.find_card(card_id)
            comment = Comment(text=text, author=author)
            card.comments.append(comment)
            card.touch()
            board.add_activity("api_comment_added", card.title)
            self.persist()
            return comment.to_dict()

    def delete_card(self, card_id: str, hard: bool = False) -> dict:
        with self.lock:
            board, column, card = self.find_card(card_id)
            if hard:
                column.cards.remove(card)
                board.add_activity("api_card_deleted", card.title)
                result = {"deleted": card_id, "hard": True}
            else:
                card.archived = True
                card.touch()
                board.add_activity("api_card_archived", card.title)
                result = card.to_dict()
            self.persist()
            return result

    def activity(self, board_id: str) -> list[dict]:
        with self.lock:
            board = self.get_board(board_id)
            return [activity.to_dict() for activity in board.activities]

    def add_activity(self, board_id: str, action: str, details: str = "") -> dict:
        with self.lock:
            board = self.get_board(board_id)
            activity = ActivityLog(action=action, details=details)
            board.activities.insert(0, activity)
            self.persist()
            return activity.to_dict()
