from __future__ import annotations

from datetime import date

from models.board import Board
from models.card import Card
from models.column import Column


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def card_matches(card: Card, query: str = "", priority: str = "Wszystkie", label: str = "Wszystkie", member: str = "", due: str = "Wszystkie") -> bool:
    if card.archived and due != "Archiwum":
        return False
    if due == "Archiwum":
        return card.archived

    q = query.strip().lower()
    if q:
        haystack = " ".join([
            card.title,
            card.description,
            " ".join(comment.text for comment in card.comments),
            " ".join(label.name for label in card.labels),
        ]).lower()
        if q not in haystack:
            return False

    if priority != "Wszystkie" and card.priority != priority:
        return False

    if label != "Wszystkie" and not any(item.name == label for item in card.labels):
        return False

    if member.strip() and member.strip().lower() not in " ".join(card.members).lower():
        return False

    if due != "Wszystkie":
        today = date.today().isoformat()
        if due == "Po terminie" and not (card.due_date and card.due_date < today):
            return False
        if due == "Dziś" and card.due_date != today:
            return False
        if due == "Bez terminu" and card.due_date:
            return False
    return True


def sort_cards(cards: list[Card], sort_by: str) -> list[Card]:
    if sort_by == "Termin":
        return sorted(cards, key=lambda c: c.due_date or "9999-12-31")
    if sort_by == "Priorytet":
        return sorted(cards, key=lambda c: PRIORITY_ORDER.get(c.priority, 9))
    if sort_by == "Data utworzenia":
        return sorted(cards, key=lambda c: c.created_at)
    if sort_by == "Alfabetycznie":
        return sorted(cards, key=lambda c: c.title.lower())
    return cards


def filtered_columns(board: Board, query: str, priority: str, label: str, member: str, due: str, sort_by: str) -> list[Column]:
    result: list[Column] = []
    for column in board.columns:
        if column.archived:
            continue
        cards = [card for card in column.cards if card_matches(card, query, priority, label, member, due)]
        result.append(Column(id=column.id, name=column.name, emoji=column.emoji, cards=sort_cards(cards, sort_by)))
    return result
