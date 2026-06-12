from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LabelPayload(BaseModel):
    name: str
    color: str = "#3b82f6"


class ChecklistItemPayload(BaseModel):
    text: str
    done: bool = False


class CommentPayload(BaseModel):
    text: str
    author: str = "API User"


class CardCreatePayload(BaseModel):
    column_id: str
    title: str = Field(min_length=1)
    description: str = ""
    priority: str = "medium"
    labels: list[LabelPayload] = Field(default_factory=list)
    due_date: str | None = None
    members: list[str] = Field(default_factory=list)
    checklist: list[ChecklistItemPayload] = Field(default_factory=list)
    cover_color: str = ""
    template: str = ""


class CardUpdatePayload(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    due_date: str | None = None
    members: list[str] | None = None
    cover_color: str | None = None
    archived: bool | None = None
    dependencies: list[str] | None = None


class CardMovePayload(BaseModel):
    target_column_id: str
    target_index: int | None = None


class ColumnCreatePayload(BaseModel):
    name: str = Field(min_length=1)
    emoji: str = ""


class BoardCreatePayload(BaseModel):
    name: str = Field(min_length=1)
    template: str = "Kanban"


class BoardUpdatePayload(BaseModel):
    name: str | None = None
    favorite: bool | None = None
    archived: bool | None = None


class WorkspaceUpdatePayload(BaseModel):
    name: str | None = None
    active_board_id: str | None = None


class PathPayload(BaseModel):
    path: str


class ApiResponse(BaseModel):
    ok: bool = True
    message: str = "OK"
    data: Any | None = None
