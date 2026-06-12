from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from models.board import Board
from models.card import Card


@dataclass
class AIResult:
    text: str
    provider: str = "offline"
    ok: bool = True


class LocalAIService:
    """Asystent AI dla Better Trello.

    Kolejność providerów:
    1. OpenRouter — jeśli ustawisz klucz `OPENROUTER_API_KEY` albo
       `BETTER_TRELLO_OPENROUTER_API_KEY`.
    2. Ollama lokalnie — jeśli działa pod `127.0.0.1:11434`.
    3. Offline fallback — zawsze działa bez internetu i bez zależności.

    OpenRouter wymaga internetu i klucza API, ale nie wymaga dodatkowych paczek,
    bo używamy standardowego `urllib`.
    """

    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434/api/generate",
        model: str = "llama3.1",
        openrouter_api_key: str | None = None,
        openrouter_model: str | None = None,
        openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions",
    ) -> None:
        self.ollama_url = ollama_url
        self.model = model
        self.openrouter_url = os.getenv("BETTER_TRELLO_OPENROUTER_URL", openrouter_url)
        self.openrouter_api_key = (
            openrouter_api_key
            or os.getenv("BETTER_TRELLO_OPENROUTER_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or ""
        )
        self.openrouter_model = (
            openrouter_model
            or os.getenv("BETTER_TRELLO_OPENROUTER_MODEL")
            or os.getenv("OPENROUTER_MODEL")
            or "openai/gpt-4o-mini"
        )
        self.openrouter_site_url = os.getenv("BETTER_TRELLO_SITE_URL", "http://127.0.0.1")
        self.openrouter_app_name = os.getenv("BETTER_TRELLO_APP_NAME", "Better Trello")

    def ask(self, prompt: str, board: Board | None = None, card: Card | None = None) -> AIResult:
        context = self._build_context(board, card)
        system_prompt = (
            "Jesteś asystentem produktywności dla aplikacji Kanban/Trello o nazwie Better Trello. "
            "Odpowiadaj po polsku, konkretnie, praktycznie i krótko. "
            "Jeżeli generujesz checklistę, wypisz same punkty w osobnych liniach."
        )
        user_prompt = f"KONTEKST:\n{context}\n\nPYTANIE:\n{prompt}"

        openrouter = self._ask_openrouter(system_prompt, user_prompt)
        if openrouter.ok:
            return openrouter

        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        ollama = self._ask_ollama(full_prompt)
        if ollama.ok:
            return ollama

        return AIResult(text=self._offline_answer(prompt, board, card), provider="offline", ok=True)

    def suggest_checklist(self, card: Card) -> list[str]:
        prompt = f"Wygeneruj checklistę 5-8 kroków dla zadania: {card.title}. Opis: {card.description}"
        result = self.ask(prompt, card=card)
        lines = []
        for line in result.text.splitlines():
            cleaned = line.strip().lstrip("-•0123456789.[] ").strip()
            if cleaned and len(cleaned) > 2:
                lines.append(cleaned)
        if len(lines) >= 3:
            return lines[:8]
        return self._offline_checklist(card)

    def summarize_board(self, board: Board) -> str:
        total = sum(len([card for card in column.cards if not card.archived]) for column in board.columns)
        done = sum(
            len([card for card in column.cards if not card.archived])
            for column in board.columns
            if "done" in column.name.lower() or "got" in column.name.lower()
        )
        overdue = [card for column in board.columns for card in column.cards if card.due_date and not card.archived]
        high = [card for column in board.columns for card in column.cards if card.priority == "high" and not card.archived]
        lines = [
            f"Tablica: {board.name}",
            f"Aktywne karty: {total}",
            f"Ukończone: {done}",
            f"Wysoki priorytet: {len(high)}",
            f"Karty z terminem: {len(overdue)}",
            "",
            "Sugestie:",
            "- Skup się najpierw na kartach high.",
            "- Przenieś ukończone checklisty do Done/Gotowe.",
            "- Uzupełnij terminy przy zadaniach bez deadline'u.",
        ]
        return "\n".join(lines)

    def split_task(self, title: str, description: str = "") -> list[str]:
        card = Card(title=title, description=description)
        return self._offline_checklist(card)

    def provider_status(self) -> dict:
        return {
            "openrouter_configured": bool(self.openrouter_api_key),
            "openrouter_model": self.openrouter_model,
            "ollama_url": self.ollama_url,
            "fallback": "offline",
        }

    def _ask_openrouter(self, system_prompt: str, user_prompt: str) -> AIResult:
        if not self.openrouter_api_key:
            return AIResult(text="", provider="openrouter", ok=False)

        payload = json.dumps(
            {
                "model": self.openrouter_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 900,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.openrouter_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "HTTP-Referer": self.openrouter_site_url,
                "X-Title": self.openrouter_app_name,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if text:
                        return AIResult(text=text, provider=f"openrouter:{self.openrouter_model}", ok=True)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            pass
        return AIResult(text="", provider="openrouter", ok=False)

    def _ask_ollama(self, prompt: str) -> AIResult:
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            self.ollama_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
                text = data.get("response", "").strip()
                if text:
                    return AIResult(text=text, provider="ollama", ok=True)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            pass
        return AIResult(text="", provider="ollama", ok=False)

    def _build_context(self, board: Board | None, card: Card | None) -> str:
        parts = []
        if board is not None:
            parts.append(self.summarize_board(board))
            parts.append("Kolumny: " + ", ".join(f"{column.name}({len(column.cards)})" for column in board.columns))
        if card is not None:
            parts.append(
                "Karta: "
                f"{card.title}; priorytet={card.priority}; termin={card.due_date or 'brak'}; "
                f"opis={card.description or 'brak'}; checklist={card.checklist_progress}%"
            )
        return "\n".join(parts) if parts else "Brak kontekstu."

    def _offline_answer(self, prompt: str, board: Board | None, card: Card | None) -> str:
        lower = prompt.lower()
        if "checklist" in lower or "kroki" in lower or "podziel" in lower:
            target = card or self._first_relevant_card(board)
            if target:
                return "\n".join(f"- {item}" for item in self._offline_checklist(target))
        if "podsum" in lower or "summary" in lower or "status" in lower:
            if board:
                return self.summarize_board(board)
        if "priorytet" in lower:
            if board:
                high = [card.title for column in board.columns for card in column.cards if card.priority == "high" and not card.archived]
                return "Najpilniejsze karty:\n" + "\n".join(f"- {title}" for title in high[:10]) if high else "Nie widzę kart z wysokim priorytetem."
        return (
            "Tryb offline AI: mogę pomóc podsumować tablicę, wygenerować checklistę, "
            "podzielić zadanie na kroki albo wskazać priorytety. Aby użyć OpenRouter, ustaw "
            "zmienną środowiskową OPENROUTER_API_KEY albo BETTER_TRELLO_OPENROUTER_API_KEY. "
            "Alternatywnie uruchom lokalnie Ollama na 127.0.0.1:11434."
        )

    def _offline_checklist(self, card: Card) -> list[str]:
        title = card.title.lower()
        if "bug" in title or "błąd" in title or "🐛" in title:
            return [
                "Opisać kroki reprodukcji",
                "Sprawdzić logi i stack trace",
                "Napisać test regresji",
                "Naprawić przyczynę błędu",
                "Zweryfikować poprawkę lokalnie",
                "Zaktualizować dokumentację, jeśli potrzeba",
            ]
        if "api" in title or "backend" in title or "jwt" in title or "auth" in title:
            return [
                "Doprecyzować kontrakt endpointu",
                "Dodać model danych / walidację",
                "Zaimplementować logikę biznesową",
                "Dodać obsługę błędów",
                "Napisać testy jednostkowe",
                "Przetestować integrację z UI",
                "Zaktualizować README/API docs",
            ]
        if "ui" in title or "frontend" in title or "widok" in title:
            return [
                "Przygotować layout komponentu",
                "Dodać stany loading/error/empty",
                "Podpiąć dane z modelu/API",
                "Dodać walidację formularzy",
                "Sprawdzić responsywność",
                "Wykonać test manualny UX",
            ]
        return [
            "Doprecyzować cel zadania",
            "Rozbić zadanie na małe kroki",
            "Zidentyfikować zależności",
            "Wykonać implementację MVP",
            "Dodać testy lub checklistę weryfikacji",
            "Zrobić review i oznaczyć jako Done",
        ]

    def _first_relevant_card(self, board: Board | None) -> Card | None:
        if board is None:
            return None
        for column in board.columns:
            for card in column.cards:
                if not card.archived:
                    return card
        return None
