from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import absolutny działa dla:
#   uvicorn api.app:app --reload
# oraz dla:
#   python api/app.py
# bo wyżej dodajemy PROJECT_ROOT do sys.path.
from api.repository import NotFoundError, ValidationError, WorkspaceRepository
from services.ai import LocalAIService


# Schematy requestów trzymamy bezpośrednio w app.py, żeby IDE nie zgłaszało
# fałszywych błędów typu "unresolved reference api.schemas". Plik
# api/schemas.py zostaje w projekcie jako osobny moduł dokumentacyjny/eksportowy.
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


class AIPromptPayload(BaseModel):
    prompt: str = Field(min_length=1)
    board_id: str | None = None
    card_id: str | None = None


class ApiResponse(BaseModel):
    ok: bool = True
    message: str = "OK"
    data: Any | None = None

app = FastAPI(
    title="Better Trello Local API",
    description="Opcjonalny lokalny REST API dla desktopowej aplikacji Better Trello. Działa lokalnie, bez kont i bez chmury.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repo = WorkspaceRepository()
ai_service = LocalAIService()


def handle_error(error: Exception) -> HTTPException:
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ValidationError):
        return HTTPException(status_code=400, detail=str(error))
    return HTTPException(status_code=500, detail=str(error))


@app.get("/health", response_model=ApiResponse)
def health() -> ApiResponse:
    return ApiResponse(data={"status": "ok", "app": "Better Trello Local API"})


@app.get("/workspace")
def get_workspace():
    return repo.workspace_dict()


@app.patch("/workspace")
def update_workspace(payload: WorkspaceUpdatePayload):
    try:
        return repo.update_workspace(name=payload.name, active_board_id=payload.active_board_id)
    except Exception as error:
        raise handle_error(error)


@app.post("/workspace/save", response_model=ApiResponse)
def save_workspace(payload: PathPayload | None = None) -> ApiResponse:
    try:
        data = repo.save_to_json(payload.path if payload else None)
        return ApiResponse(message="Workspace zapisany", data=data)
    except Exception as error:
        raise handle_error(error)


@app.post("/workspace/load")
def load_workspace(payload: PathPayload):
    try:
        return repo.load_from_json(payload.path)
    except Exception as error:
        raise handle_error(error)


@app.get("/boards")
def list_boards(include_archived: bool = False):
    return repo.boards(include_archived=include_archived)


@app.post("/boards", status_code=201)
def create_board(payload: BoardCreatePayload):
    try:
        return repo.create_board(payload.name, payload.template)
    except Exception as error:
        raise handle_error(error)


@app.get("/boards/{board_id}")
def get_board(board_id: str):
    try:
        return repo.board_dict(board_id)
    except Exception as error:
        raise handle_error(error)


@app.patch("/boards/{board_id}")
def update_board(board_id: str, payload: BoardUpdatePayload):
    try:
        return repo.update_board(board_id, **payload.dict(exclude_unset=True))
    except Exception as error:
        raise handle_error(error)


@app.delete("/boards/{board_id}")
def delete_board(board_id: str, hard: bool = False):
    try:
        return repo.delete_board(board_id, hard=hard)
    except Exception as error:
        raise handle_error(error)


@app.post("/boards/{board_id}/columns", status_code=201)
def create_column(board_id: str, payload: ColumnCreatePayload):
    try:
        return repo.create_column(board_id, payload.name, payload.emoji)
    except Exception as error:
        raise handle_error(error)


@app.get("/boards/{board_id}/cards")
def list_cards(board_id: str, query: str = "", include_archived: bool = False):
    try:
        return repo.cards(board_id, query=query, include_archived=include_archived)
    except Exception as error:
        raise handle_error(error)


@app.post("/boards/{board_id}/cards", status_code=201)
def create_card(board_id: str, payload: CardCreatePayload):
    try:
        return repo.create_card(board_id, payload.dict())
    except Exception as error:
        raise handle_error(error)


@app.get("/cards/{card_id}")
def get_card(card_id: str):
    try:
        _board, column, card = repo.find_card(card_id)
        data = card.to_dict()
        data["column_id"] = column.id
        data["column_name"] = column.name
        return data
    except Exception as error:
        raise handle_error(error)


@app.patch("/cards/{card_id}")
def update_card(card_id: str, payload: CardUpdatePayload):
    try:
        return repo.update_card(card_id, payload.dict(exclude_unset=True))
    except Exception as error:
        raise handle_error(error)


@app.post("/cards/{card_id}/move")
def move_card(card_id: str, payload: CardMovePayload):
    try:
        return repo.move_card_to_column(card_id, payload.target_column_id, payload.target_index)
    except Exception as error:
        raise handle_error(error)


@app.post("/cards/{card_id}/comments", status_code=201)
def add_comment(card_id: str, payload: CommentPayload):
    try:
        return repo.add_comment(card_id, payload.text, payload.author)
    except Exception as error:
        raise handle_error(error)


@app.delete("/cards/{card_id}")
def delete_card(card_id: str, hard: bool = False):
    try:
        return repo.delete_card(card_id, hard=hard)
    except Exception as error:
        raise handle_error(error)


@app.get("/boards/{board_id}/activity")
def board_activity(board_id: str):
    try:
        return repo.activity(board_id)
    except Exception as error:
        raise handle_error(error)


@app.get("/search/cards")
def search_cards(query: str = Query(min_length=1), board_id: str | None = None, include_archived: bool = False):
    try:
        boards = [repo.get_board(board_id)] if board_id else repo.workspace.boards
        result = []
        for board in boards:
            result.extend(repo.cards(board.id, query=query, include_archived=include_archived))
        return result
    except Exception as error:
        raise handle_error(error)


@app.get("/ai/status", response_model=ApiResponse)
def ai_status() -> ApiResponse:
    return ApiResponse(data=ai_service.provider_status())


@app.post("/ai/chat", response_model=ApiResponse)
def ai_chat(payload: AIPromptPayload) -> ApiResponse:
    try:
        board = repo.get_board(payload.board_id) if payload.board_id else repo.workspace.active_board
        card = None
        if payload.card_id:
            _board, _column, card = repo.find_card(payload.card_id)
        result = ai_service.ask(payload.prompt, board=board, card=card)
        return ApiResponse(message=f"provider={result.provider}", data={"text": result.text, "provider": result.provider})
    except Exception as error:
        raise handle_error(error)


@app.post("/ai/cards/{card_id}/checklist", response_model=ApiResponse)
def ai_card_checklist(card_id: str) -> ApiResponse:
    try:
        _board, _column, card = repo.find_card(card_id)
        items = ai_service.suggest_checklist(card)
        return ApiResponse(message="Checklist generated", data={"items": items})
    except Exception as error:
        raise handle_error(error)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True)
