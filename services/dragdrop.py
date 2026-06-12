from __future__ import annotations

from models.card import Card
from models.column import Column


def move_card(card: Card, source: Column, target: Column, target_index: int | None = None) -> None:
    """Przenosi kartę między kolumnami i aktualizuje model danych."""
    if card not in source.cards:
        return

    source.cards.remove(card)

    if target_index is None or target_index < 0 or target_index > len(target.cards):
        target.cards.append(card)
    else:
        target.cards.insert(target_index, card)
