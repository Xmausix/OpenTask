from __future__ import annotations

from datetime import date, timedelta

from models.board import Board


def due_notifications(board: Board) -> list[str]:
    """Zwraca lokalne komunikaty o terminach kart.

    Funkcja nie korzysta z internetu ani zewnętrznych bibliotek. Jest używana
    przez UI do pokazania prostego ostrzeżenia w pasku tytułu aplikacji.
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)
    messages: list[str] = []

    for column in board.columns:
        for card in column.cards:
            if card.archived or not card.due_date:
                continue
            try:
                due = date.fromisoformat(card.due_date)
            except ValueError:
                continue

            if due < today:
                messages.append(f"Termin minął: {card.title} ({card.due_date})")
            elif due == today:
                messages.append(f"Termin dziś: {card.title}")
            elif due == tomorrow:
                messages.append(f"Termin za 1 dzień: {card.title}")

    return messages
