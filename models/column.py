from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from models.card import Card


@dataclass
class Column:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Nowa kolumna"
    cards: list[Card] = field(default_factory=list)
    emoji: str = ""
    archived: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "cards": [card.to_dict() for card in self.cards],
            "emoji": self.emoji,
            "archived": self.archived,
        }

    @staticmethod
    def from_dict(data: dict) -> "Column":
        return Column(
            id=data.get("id") or str(uuid4()),
            name=data.get("name", "Nowa kolumna"),
            cards=[Card.from_dict(card) for card in data.get("cards", [])],
            emoji=data.get("emoji", ""),
            archived=bool(data.get("archived", False)),
        )
