from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


@dataclass
class ActivityLog:
    id: str = field(default_factory=lambda: str(uuid4()))
    action: str = ""
    details: str = ""
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "details": self.details,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "ActivityLog":
        return ActivityLog(
            id=data.get("id") or str(uuid4()),
            action=data.get("action", ""),
            details=data.get("details", ""),
            created_at=data.get("created_at") or now_iso(),
        )
