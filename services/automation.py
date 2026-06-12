from __future__ import annotations

from datetime import date

from models.board import Board
from models.label import Label


def _get_or_create_label(board: Board, name: str, color: str) -> Label:
    for label in board.labels:
        if label.name.lower() == name.lower():
            return label
    label = Label(name=name, color=color)
    board.labels.append(label)
    return label


def apply_default_automations(board: Board) -> list[str]:
    """Lokalne automatyzacje bez internetu.

    Reguły MVP:
    - etykieta `Critical` ustawia priorytet `high`,
    - karta po terminie dostaje etykietę `Overdue`,
    - karta ukończona dostaje etykietę `Done`,
    - karta z checklistą 100% w kolumnie nieukończonej dostaje etykietę `Ready`.
    """
    today = date.today().isoformat()
    changes: list[str] = []
    overdue_label = _get_or_create_label(board, "Overdue", "#dc2626")
    done_label = _get_or_create_label(board, "Done", "#16a34a")
    ready_label = _get_or_create_label(board, "Ready", "#0ea5e9")

    for column in board.columns:
        is_done_column = "done" in column.name.lower() or "got" in column.name.lower()
        for card in column.cards:
            if card.archived:
                continue
            label_names = {label.name.lower() for label in card.labels}
            if "critical" in label_names and card.priority != "high":
                card.priority = "high"
                card.touch()
                changes.append(f"{card.title}: Critical → high")
            if card.due_date and card.due_date < today and "overdue" not in label_names:
                card.labels.append(overdue_label)
                card.touch()
                changes.append(f"{card.title}: dodano Overdue")
            if is_done_column and "done" not in label_names:
                card.labels.append(done_label)
                card.touch()
                changes.append(f"{card.title}: dodano Done")
            if card.checklist and card.checklist_progress == 100 and not is_done_column and "ready" not in label_names:
                card.labels.append(ready_label)
                card.touch()
                changes.append(f"{card.title}: dodano Ready")

    if changes:
        board.add_activity("automations_applied", f"Zastosowano {len(changes)} zmian")
    return changes

