from __future__ import annotations

from copy import deepcopy

from models.workspace import Workspace


class HistoryService:
    """Prosty lokalny stos undo/redo oparty o migawki Workspace.

    Tkinter nie ma wbudowanego mechanizmu cofania zmian modelu. Dla aplikacji
    lokalnej i plików JSON najbezpieczniejszy MVP to snapshot całego workspace
    przed operacją mutującą.
    """

    def __init__(self, workspace: Workspace, limit: int = 50) -> None:
        self.limit = limit
        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []
        self.reset(workspace)

    def reset(self, workspace: Workspace) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_snapshot = deepcopy(workspace.to_dict())

    def push(self, workspace: Workspace) -> None:
        self.undo_stack.append(deepcopy(workspace.to_dict()))
        if len(self.undo_stack) > self.limit:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.current_snapshot = deepcopy(workspace.to_dict())

    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        return bool(self.redo_stack)

    def undo(self, workspace: Workspace) -> Workspace | None:
        if not self.undo_stack:
            return None
        self.redo_stack.append(deepcopy(workspace.to_dict()))
        snapshot = self.undo_stack.pop()
        restored = Workspace.from_dict(snapshot)
        self.current_snapshot = deepcopy(restored.to_dict())
        return restored

    def redo(self, workspace: Workspace) -> Workspace | None:
        if not self.redo_stack:
            return None
        self.undo_stack.append(deepcopy(workspace.to_dict()))
        snapshot = self.redo_stack.pop()
        restored = Workspace.from_dict(snapshot)
        self.current_snapshot = deepcopy(restored.to_dict())
        return restored
