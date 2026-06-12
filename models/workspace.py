from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from models.board import Board


@dataclass
class Workspace:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Better Trello"
    boards: list[Board] = field(default_factory=list)
    active_board_id: str | None = None

    @staticmethod
    def default() -> "Workspace":
        board = Board.default()
        return Workspace(boards=[board], active_board_id=board.id)

    @property
    def active_board(self) -> Board | None:
        if self.active_board_id:
            for board in self.boards:
                if board.id == self.active_board_id:
                    return board
        return next((board for board in self.boards if not board.archived), None)

    def add_board(self, board: Board) -> None:
        self.boards.append(board)
        self.active_board_id = board.id

    def visible_boards(self, include_archived: bool = False) -> list[Board]:
        boards = self.boards if include_archived else [board for board in self.boards if not board.archived]
        return sorted(boards, key=lambda b: (not b.favorite, b.name.lower()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "active_board_id": self.active_board_id,
            "boards": [board.to_dict() for board in self.boards],
        }

    @staticmethod
    def from_dict(data: dict) -> "Workspace":
        # Wsteczna kompatybilność: pojedynczy board JSON może zostać otwarty jako workspace.
        if "columns" in data and "boards" not in data:
            board = Board.from_dict(data)
            return Workspace(boards=[board], active_board_id=board.id)
        workspace = Workspace(
            id=data.get("id") or str(uuid4()),
            name=data.get("name", "Better Trello"),
            boards=[Board.from_dict(board) for board in data.get("boards", [])],
            active_board_id=data.get("active_board_id"),
        )
        if not workspace.boards:
            workspace = Workspace.default()
        if not workspace.active_board_id and workspace.boards:
            workspace.active_board_id = workspace.boards[0].id
        return workspace
