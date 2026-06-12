from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import uuid4

from models.attachment import Attachment
from models.checklist import ChecklistItem
from models.comment import Comment
from models.label import Label


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


@dataclass
class Card:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    priority: str = "medium"
    labels: list[Label] = field(default_factory=list)
    due_date: str | None = None
    members: list[str] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    checklist: list[ChecklistItem] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    cover_color: str = ""
    archived: bool = False
    created_at: str = field(default_factory=today_iso)
    updated_at: str = field(default_factory=now_iso)
    dependencies: list[str] = field(default_factory=list)
    template: str = ""

    def touch(self) -> None:
        self.updated_at = now_iso()

    @property
    def checklist_progress(self) -> int:
        if not self.checklist:
            return 0
        done = sum(1 for item in self.checklist if item.done)
        return round((done / len(self.checklist)) * 100)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "labels": [label.to_dict() for label in self.labels],
            "due_date": self.due_date,
            "members": self.members,
            "attachments": [attachment.to_dict() for attachment in self.attachments],
            "checklist": [item.to_dict() for item in self.checklist],
            "comments": [comment.to_dict() for comment in self.comments],
            "cover_color": self.cover_color,
            "archived": self.archived,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "dependencies": self.dependencies,
            "template": self.template,
        }

    @staticmethod
    def from_dict(data: dict) -> "Card":
        return Card(
            id=data.get("id") or str(uuid4()),
            title=data.get("title", ""),
            description=data.get("description", ""),
            priority=data.get("priority", "medium"),
            labels=[Label.from_dict(label) for label in data.get("labels", [])],
            due_date=data.get("due_date"),
            members=list(data.get("members", [])),
            attachments=[Attachment.from_dict(item) for item in data.get("attachments", [])],
            checklist=[ChecklistItem.from_dict(item) for item in data.get("checklist", [])],
            comments=[Comment.from_dict(comment) for comment in data.get("comments", [])],
            cover_color=data.get("cover_color", ""),
            archived=bool(data.get("archived", False)),
            created_at=data.get("created_at", today_iso()),
            updated_at=data.get("updated_at", now_iso()),
            dependencies=list(data.get("dependencies", [])),
            template=data.get("template", ""),
        )
