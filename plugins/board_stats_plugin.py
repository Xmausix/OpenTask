from __future__ import annotations

from tkinter import messagebox

PLUGIN = {
    "name": "Board Stats",
    "version": "1.0.0",
    "description": "Pokazuje szybkie statystyki aktualnej tablicy.",
    "author": "Better Trello",
}


def register(context):
    def show_stats():
        board = context.board
        active_cards = [card for column in board.columns for card in column.cards if not card.archived]
        archived_cards = [card for column in board.columns for card in column.cards if card.archived]
        high_cards = [card for card in active_cards if card.priority == "high"]
        checklist_cards = [card for card in active_cards if card.checklist]
        avg_progress = round(sum(card.checklist_progress for card in checklist_cards) / len(checklist_cards)) if checklist_cards else 0
        text = (
            f"Tablica: {board.name}\n"
            f"Kolumny: {len(board.columns)}\n"
            f"Aktywne karty: {len(active_cards)}\n"
            f"Archiwum: {len(archived_cards)}\n"
            f"High priority: {len(high_cards)}\n"
            f"Średni progress checklist: {avg_progress}%"
        )
        messagebox.showinfo("Board Stats", text)

    context.add_command("Statystyki tablicy", show_stats)

    def on_card_added(card=None, **_kwargs):
        if card is not None:
            context.status(f"Plugin Stats: dodano kartę {card.title}")

    context.add_hook("card_added", on_card_added)
