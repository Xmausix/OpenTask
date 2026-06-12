from __future__ import annotations

from models.label import Label

PLUGIN = {
    "name": "Auto Label",
    "version": "1.0.0",
    "description": "Automatycznie dodaje etykiety Backend/UI/Bug na podstawie tytułu karty.",
    "author": "Better Trello",
}


def _ensure_label(board, name: str, color: str):
    for label in board.labels:
        if label.name.lower() == name.lower():
            return label
    label = Label(name=name, color=color)
    board.labels.append(label)
    return label


def register(context):
    def classify(card, board):
        title = f"{card.title} {card.description}".lower()
        candidates = []
        if any(word in title for word in ["api", "backend", "jwt", "auth", "database"]):
            candidates.append(_ensure_label(board, "Backend", "#22c55e"))
        if any(word in title for word in ["ui", "frontend", "widok", "navbar", "dashboard"]):
            candidates.append(_ensure_label(board, "Frontend", "#f59e0b"))
        if any(word in title for word in ["bug", "błąd", "fix", "error"]):
            candidates.append(_ensure_label(board, "Bug", "#a855f7"))
        existing = {label.name.lower() for label in card.labels}
        added = 0
        for label in candidates:
            if label.name.lower() not in existing:
                card.labels.append(label)
                added += 1
        if added:
            card.touch()
            context.status(f"Auto Label: dodano {added} etykiet do {card.title}")
            context.refresh()

    def on_card_added(board=None, card=None, **_kwargs):
        if board is not None and card is not None:
            classify(card, board)

    def classify_existing():
        board = context.board
        for column in board.columns:
            for card in column.cards:
                if not card.archived:
                    classify(card, board)
        context.status("Auto Label: klasyfikacja zakończona")

    context.add_hook("card_added", on_card_added)
    context.add_command("Auto Label: klasyfikuj tablicę", classify_existing)
