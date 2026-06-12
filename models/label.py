from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Label:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    color: str = "#3b82f6"

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color}

    @staticmethod
    def from_dict(data: dict | str) -> "Label":
        if isinstance(data, str):
            return Label(name=data)
        return Label(
            id=data.get("id") or str(uuid4()),
            name=data.get("name", ""),
            color=data.get("color", "#3b82f6"),
        )
