from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from models.card import Card
from models.column import Column
from ui.card_view import CardView


class ColumnView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        column: Column,
        add_card_callback: Callable[[Column], None],
        rename_callback: Callable[[Column], None],
        delete_callback: Callable[[Column], None],
        move_left_callback: Callable[[Column], None],
        move_right_callback: Callable[[Column], None],
        edit_card_callback: Callable[[Card], None],
        preview_card_callback: Callable[[Card], None],
        archive_card_callback: Callable[[Card], None],
        duplicate_card_callback: Callable[[Card], None],
        delete_card_callback: Callable[[Card], None],
        drag_start_callback,
        drag_motion_callback,
        drag_release_callback,
    ) -> None:
        super().__init__(master, style="Column.TFrame", padding=8)
        self.column = column
        self.card_views: list[CardView] = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="ColumnHeader.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)

        name = f"{column.emoji} {column.name}" if column.emoji else column.name
        title = ttk.Label(header, text=name, style="ColumnTitle.TLabel")
        title.grid(row=0, column=0, sticky="w")

        menu_button = ttk.Menubutton(header, text="⋯", width=3)
        menu = tk.Menu(menu_button, tearoff=False)
        menu.add_command(label="Zmień nazwę", command=lambda: rename_callback(column))
        menu.add_command(label="Przesuń w lewo", command=lambda: move_left_callback(column))
        menu.add_command(label="Przesuń w prawo", command=lambda: move_right_callback(column))
        menu.add_separator()
        menu.add_command(label="Usuń kolumnę", command=lambda: delete_callback(column))
        menu_button["menu"] = menu
        menu_button.grid(row=0, column=1, sticky="e")

        self.cards_frame = ttk.Frame(self, style="ColumnBody.TFrame")
        self.cards_frame.grid(row=1, column=0, sticky="nsew")
        self.cards_frame.columnconfigure(0, weight=1)

        for index, card in enumerate(column.cards):
            card_view = CardView(
                self.cards_frame,
                card,
                drag_start_callback,
                drag_motion_callback,
                drag_release_callback,
                edit_card_callback,
                preview_card_callback,
                archive_card_callback,
                duplicate_card_callback,
                delete_card_callback,
            )
            card_view.grid(row=index, column=0, sticky="ew", pady=(0, 8))
            self.card_views.append(card_view)

        ttk.Button(self, text="+ Karta", command=lambda: add_card_callback(column)).grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def contains_screen_point(self, x_root: int, y_root: int) -> bool:
        left = self.winfo_rootx()
        top = self.winfo_rooty()
        right = left + self.winfo_width()
        bottom = top + self.winfo_height()
        return left <= x_root <= right and top <= y_root <= bottom
