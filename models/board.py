from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from uuid import uuid4

from models.activity import ActivityLog
from models.card import Card
from models.column import Column
from models.label import Label


@dataclass
class Board:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Projekt WWW"
    columns: list[Column] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    favorite: bool = False
    archived: bool = False
    activities: list[ActivityLog] = field(default_factory=list)

    @staticmethod
    def default() -> "Board":
        labels = [
            Label(name="Backend", color="#22c55e"),
            Label(name="API", color="#3b82f6"),
            Label(name="Bug", color="#a855f7"),
            Label(name="Critical", color="#ef4444"),
        ]
        return Board(
            name="Projekt WWW",
            labels=labels,
            columns=[
                Column(name="Do zrobienia", emoji="📋", cards=[
                    Card(title="Login", description="Implementacja JWT", priority="high", labels=[labels[0], labels[3]], due_date="2026-07-01"),
                    Card(title="Dashboard", description="Widok główny aplikacji", priority="medium", labels=[labels[1]]),
                ]),
                Column(name="W trakcie", emoji="🚧", cards=[
                    Card(title="API", description="Endpointy REST", priority="medium", labels=[labels[1]]),
                    Card(title="Auth", description="Autoryzacja użytkownika", priority="high", labels=[labels[0]]),
                ]),
                Column(name="Gotowe", emoji="✅", cards=[
                    Card(title="UI", description="Makietowanie ekranów", priority="low"),
                    Card(title="Navbar", description="Menu nawigacyjne", priority="low"),
                ]),
            ],
        )

    def clone(self) -> "Board":
        copied = deepcopy(self)
        copied.id = str(uuid4())
        copied.name = f"{self.name} — kopia"
        copied.favorite = False
        copied.archived = False
        copied.activities.append(ActivityLog(action="board_copied", details=f"Skopiowano z tablicy {self.name}"))
        return copied

    def add_activity(self, action: str, details: str = "") -> None:
        self.activities.insert(0, ActivityLog(action=action, details=details))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "board": self.name,
            "columns": [column.to_dict() for column in self.columns],
            "labels": [label.to_dict() for label in self.labels],
            "favorite": self.favorite,
            "archived": self.archived,
            "activities": [activity.to_dict() for activity in self.activities],
        }

    @staticmethod
    def from_dict(data: dict) -> "Board":
        return Board(
            id=data.get("id") or str(uuid4()),
            name=data.get("board") or data.get("name", "Projekt WWW"),
            columns=[Column.from_dict(column) for column in data.get("columns", [])],
            labels=[Label.from_dict(label) for label in data.get("labels", [])],
            favorite=bool(data.get("favorite", False)),
            archived=bool(data.get("archived", False)),
            activities=[ActivityLog.from_dict(activity) for activity in data.get("activities", [])],
        )
