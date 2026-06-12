from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4


@dataclass
class Attachment:
    id: str = field(default_factory=lambda: str(uuid4()))
    path: str = ""
    name: str = ""

    def __post_init__(self) -> None:
        if self.path and not self.name:
            self.name = Path(self.path).name

    def to_dict(self) -> dict:
        return {"id": self.id, "path": self.path, "name": self.name or Path(self.path).name}

    @staticmethod
    def from_dict(data: dict | str) -> "Attachment":
        if isinstance(data, str):
            return Attachment(path=data)
        return Attachment(
            id=data.get("id") or str(uuid4()),
            path=data.get("path", ""),
            name=data.get("name", ""),
        )
