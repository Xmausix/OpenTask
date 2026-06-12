from __future__ import annotations

from models.board import Board
from models.card import Card
from models.checklist import ChecklistItem
from models.column import Column
from models.label import Label


CARD_TEMPLATES: dict[str, dict] = {
    "Bug": {
        "title": "🐛 Bug",
        "description": "Kroki reprodukcji:\nOczekiwany rezultat:\nAktualny rezultat:",
        "priority": "high",
        "labels": [Label(name="Bug", color="#a855f7"), Label(name="Critical", color="#ef4444")],
        "checklist": [ChecklistItem(text="Reprodukcja"), ChecklistItem(text="Fix"), ChecklistItem(text="Test regresji")],
    },
    "Feature": {
        "title": "✨ Feature",
        "description": "Opis funkcji:\nKryteria akceptacji:",
        "priority": "medium",
        "labels": [Label(name="Frontend", color="#f59e0b")],
        "checklist": [ChecklistItem(text="Projekt"), ChecklistItem(text="Implementacja"), ChecklistItem(text="Testy")],
    },
    "Documentation": {
        "title": "📚 Dokumentacja",
        "description": "Zakres dokumentacji:",
        "priority": "low",
        "labels": [Label(name="Docs", color="#64748b")],
        "checklist": [ChecklistItem(text="Draft"), ChecklistItem(text="Review"), ChecklistItem(text="Publikacja")],
    },
    "Meeting": {
        "title": "🗓️ Meeting",
        "description": "Agenda:\nUstalenia:\nFollow-up:",
        "priority": "medium",
        "labels": [],
        "checklist": [ChecklistItem(text="Agenda"), ChecklistItem(text="Notatki"), ChecklistItem(text="Action items")],
    },
}


BOARD_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "Kanban": [("📋", "Do zrobienia"), ("🚧", "W trakcie"), ("✅", "Gotowe")],
    "Scrum": [("📥", "Backlog"), ("🚀", "Sprint"), ("🔍", "Review"), ("✅", "Done")],
    "CRM": [("🎯", "Leads"), ("💬", "Kontakt"), ("📄", "Oferta"), ("🤝", "Wygrane")],
    "Content Marketing": [("💡", "Pomysły"), ("✍️", "Pisanie"), ("🧪", "Review"), ("📢", "Opublikowane")],
    "Software Development": [("📥", "Backlog"), ("🧠", "Analysis"), ("💻", "Development"), ("🧪", "Testing"), ("✅", "Done")],
}


def create_card_from_template(template_name: str) -> Card:
    data = CARD_TEMPLATES.get(template_name, CARD_TEMPLATES["Feature"])
    return Card(
        title=data["title"],
        description=data["description"],
        priority=data["priority"],
        labels=list(data["labels"]),
        checklist=list(data["checklist"]),
        template=template_name,
    )


def create_board_from_template(name: str, template_name: str = "Kanban") -> Board:
    columns = [Column(name=column_name, emoji=emoji) for emoji, column_name in BOARD_TEMPLATES.get(template_name, BOARD_TEMPLATES["Kanban"])]
    return Board(name=name, columns=columns)
