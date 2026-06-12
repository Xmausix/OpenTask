from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from models.board import Board
from models.card import Card
from services.ai import LocalAIService


class AIChatWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        board_provider: Callable[[], Board],
        selected_card_provider: Callable[[], Card | None],
        apply_checklist_callback: Callable[[Card, list[str]], None],
    ) -> None:
        super().__init__(master)
        self.title("AI Chat — Better Trello")
        self.geometry("720x620")
        self.minsize(560, 460)
        self.board_provider = board_provider
        self.selected_card_provider = selected_card_provider
        self.apply_checklist_callback = apply_checklist_callback
        self.ai = LocalAIService()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.output = tk.Text(self, wrap="word", state="disabled", bg="#0f172a", fg="#e5e7eb", insertbackground="#ffffff")
        self.output.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 6))

        shortcuts = ttk.Frame(self)
        shortcuts.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        ttk.Button(shortcuts, text="Podsumuj tablicę", command=self.summarize_board).pack(side="left", padx=(0, 6))
        ttk.Button(shortcuts, text="Checklist dla karty", command=self.suggest_checklist).pack(side="left", padx=(0, 6))
        ttk.Button(shortcuts, text="Priorytety", command=lambda: self.ask_text("Wskaż najważniejsze priorytety na tej tablicy")).pack(side="left", padx=(0, 6))
        ttk.Button(shortcuts, text="Pomoc", command=self.show_help).pack(side="left")

        input_frame = ttk.Frame(self)
        input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_var)
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(input_frame, text="Wyślij", command=self.send).grid(row=0, column=1)
        self.input_entry.bind("<Return>", lambda _event: self.send())

        status = self.ai.provider_status()
        provider_hint = "OpenRouter skonfigurowany" if status["openrouter_configured"] else "OpenRouter nie ma klucza API — użyję Ollama albo offline fallback"
        self._append("AI", f"Cześć! Jestem asystentem Better Trello. Mogę podsumować tablicę, wygenerować checklistę albo pomóc zaplanować zadanie.\n\nStatus: {provider_hint}. Model OpenRouter: {status['openrouter_model']}.")
        self.input_entry.focus_set()

    def send(self) -> None:
        prompt = self.input_var.get().strip()
        if not prompt:
            return
        self.input_var.set("")
        self.ask_text(prompt)

    def ask_text(self, prompt: str) -> None:
        self._append("Ty", prompt)
        result = self.ai.ask(prompt, board=self.board_provider(), card=self.selected_card_provider())
        self._append(f"AI ({result.provider})", result.text)

    def summarize_board(self) -> None:
        self._append("Ty", "Podsumuj tablicę")
        self._append("AI", self.ai.summarize_board(self.board_provider()))

    def suggest_checklist(self) -> None:
        card = self.selected_card_provider()
        if card is None:
            self._append("AI", "Najpierw wybierz kartę przez Podgląd karty albo prawy klik → Podgląd.")
            return
        items = self.ai.suggest_checklist(card)
        self._append("AI", "Proponowana checklista:\n" + "\n".join(f"- {item}" for item in items))
        self.apply_checklist_callback(card, items)
        self._append("AI", "Dodałem brakujące pozycje checklisty do wybranej karty.")

    def show_help(self) -> None:
        self._append(
            "AI",
            "Przykłady pytań:\n"
            "- Podziel zadanie na kroki\n"
            "- Wygeneruj checklistę dla wybranej karty\n"
            "- Podsumuj status tablicy\n"
            "- Co powinno mieć najwyższy priorytet?\n\n"
            "OpenRouter: ustaw OPENROUTER_API_KEY albo BETTER_TRELLO_OPENROUTER_API_KEY.\n"
            "Model możesz zmienić przez OPENROUTER_MODEL albo BETTER_TRELLO_OPENROUTER_MODEL.\n"
            "Jeżeli nie ma OpenRouter, aplikacja spróbuje Ollama na 127.0.0.1:11434. W innym przypadku działa tryb offline.",
        )

    def _append(self, author: str, text: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", f"\n{author}:\n{text}\n")
        self.output.insert("end", "─" * 70 + "\n")
        self.output.configure(state="disabled")
        self.output.see("end")
