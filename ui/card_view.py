from __future__ import annotations

import tkinter as tk
from datetime import date
from typing import Callable

from models.card import Card


PRIORITY_META = {
    "low": ("🟢", "#d9f7df", "#2d8a3e"),
    "medium": ("🟡", "#fff4c2", "#9a7b00"),
    "high": ("🔴", "#ffe0e0", "#b00020"),
}


def due_color(card: Card) -> str:
    if not card.due_date:
        return "#6b7280"
    today = date.today().isoformat()
    if card.due_date < today:
        return "#dc2626"
    if card.due_date == today:
        return "#f59e0b"
    return "#16a34a"


class CardView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        card: Card,
        on_drag_start: Callable[["CardView", tk.Event], None],
        on_drag_motion: Callable[["CardView", tk.Event], None],
        on_drag_release: Callable[["CardView", tk.Event], None],
        on_edit: Callable[[Card], None],
        on_preview: Callable[[Card], None],
        on_archive: Callable[[Card], None],
        on_duplicate: Callable[[Card], None],
        on_delete: Callable[[Card], None],
    ) -> None:
        emoji, bg, accent = PRIORITY_META.get(card.priority, PRIORITY_META["medium"])
        if card.cover_color:
            bg = card.cover_color
        super().__init__(master, bg=bg, bd=1, relief="solid", cursor="hand2")
        self.card = card
        self.on_edit = on_edit
        self.on_preview = on_preview
        self.on_archive = on_archive
        self.on_duplicate = on_duplicate
        self.columnconfigure(0, weight=1)

        label_line = " ".join(f"● {label.name}" for label in card.labels[:3])
        if label_line:
            tk.Label(self, text=label_line, bg=bg, fg="#111827", anchor="w", font=("TkDefaultFont", 8)).grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))

        title_row = 1 if label_line else 0
        tk.Label(self, text=f"{emoji} {card.title}", bg=bg, fg="#1f2937", anchor="w", font=("TkDefaultFont", 10, "bold"), wraplength=200, justify="left").grid(row=title_row, column=0, sticky="ew", padx=8, pady=(6, 1))

        if card.description:
            tk.Label(self, text=card.description, bg=bg, fg="#374151", anchor="w", wraplength=200, justify="left").grid(row=title_row + 1, column=0, sticky="ew", padx=8, pady=(0, 4))

        meta_parts = []
        if card.due_date:
            meta_parts.append(f"📅 {card.due_date}")
        if card.attachments:
            meta_parts.append(f"📎 {len(card.attachments)}")
        if card.comments:
            meta_parts.append(f"💬 {len(card.comments)}")
        if card.checklist:
            meta_parts.append(f"☑ {card.checklist_progress}%")
        if card.members:
            meta_parts.append(f"👤 {', '.join(card.members[:2])}")
        if meta_parts:
            tk.Label(self, text="  ".join(meta_parts), bg=bg, fg=due_color(card), anchor="w", font=("TkDefaultFont", 8), wraplength=200, justify="left").grid(row=title_row + 2, column=0, sticky="ew", padx=8, pady=(0, 7))

        marker = tk.Frame(self, bg=accent, width=4)
        marker.grid(row=0, column=1, rowspan=4, sticky="ns")

        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Podgląd taska", command=lambda: on_preview(card))
        menu.add_command(label="Otwórz / edytuj", command=lambda: on_edit(card))
        menu.add_command(label="Duplikuj kartę", command=lambda: on_duplicate(card))
        menu.add_command(label="Przywróć kartę" if card.archived else "Archiwizuj kartę", command=lambda: on_archive(card))
        menu.add_separator()
        menu.add_command(label="Usuń na stałe", command=lambda: on_delete(card))
        self.context_menu = menu

        for widget in self.winfo_children() + [self]:
            widget.bind("<Double-Button-1>", lambda _event, c=card: on_preview(c))
            widget.bind("<Button-3>", self._show_context_menu)
            widget.bind("<Button-1>", lambda event, cv=self: on_drag_start(cv, event))
            widget.bind("<B1-Motion>", lambda event, cv=self: on_drag_motion(cv, event))
            widget.bind("<ButtonRelease-1>", lambda event, cv=self: on_drag_release(cv, event))

    def _show_context_menu(self, event) -> None:
        self.context_menu.tk_popup(event.x_root, event.y_root)
