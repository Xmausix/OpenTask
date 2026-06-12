from __future__ import annotations

PLUGIN = {
    "name": "AI Shortcut",
    "version": "1.0.0",
    "description": "Dodaje szybki skrót do AI Chat w menu Plugins.",
    "author": "Better Trello",
}


def register(context):
    context.add_command("Otwórz AI Chat", context.open_ai_chat)

    def on_card_moved(card=None, target=None, **_kwargs):
        if card is not None and target is not None:
            context.status(f"AI Plugin: karta {card.title} przeniesiona do {target.name}")

    context.add_hook("card_moved", on_card_moved)
