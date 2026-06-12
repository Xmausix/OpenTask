from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Sprint:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Sprint"
    start_date: str | None = None
    end_date: str | None = None
    card_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "card_ids": self.card_ids,
        }

    @staticmethod
    def from_dict(data: dict) -> "Sprint":
        return Sprint(
            id=data.get("id") or str(uuid4()),
            name=data.get("name", "Sprint"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            card_ids=list(data.get("card_ids", [])),
        )
