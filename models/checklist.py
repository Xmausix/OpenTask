from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ChecklistItem:
    id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    done: bool = False

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "done": self.done}

    @staticmethod
    def from_dict(data: dict) -> "ChecklistItem":
        return ChecklistItem(
            id=data.get("id") or str(uuid4()),
            text=data.get("text", ""),
            done=bool(data.get("done", False)),
        )
