from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


@dataclass
class Comment:
    id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    author: str = "Local User"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "author": self.author,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Comment":
        return Comment(
            id=data.get("id") or str(uuid4()),
            text=data.get("text", ""),
            author=data.get("author", "Local User"),
            created_at=data.get("created_at") or now_iso(),
        )
