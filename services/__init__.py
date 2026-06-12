"""Serwisy aplikacyjne Local Trello Pro."""

from __future__ import annotations

try:
    from services.ai import AIResult, LocalAIService
except ModuleNotFoundError:  # pragma: no cover
    AIResult = None  # type: ignore[assignment]
    LocalAIService = None  # type: ignore[assignment]

try:
    from services.automation import apply_default_automations
except ModuleNotFoundError:  # pragma: no cover
    def apply_default_automations(_board):
        return []

try:
    from services.backup import BackupService
except ModuleNotFoundError:  # pragma: no cover
    BackupService = None  # type: ignore[assignment]

try:
    from services.dragdrop import move_card
except ModuleNotFoundError:  # pragma: no cover
    move_card = None  # type: ignore[assignment]

try:
    from services.export import ExportService
except ModuleNotFoundError:  # pragma: no cover
    ExportService = None  # type: ignore[assignment]

try:
    from services.history import HistoryService
except ModuleNotFoundError:  # pragma: no cover
    HistoryService = None  # type: ignore[assignment]

try:
    from services.notifications import due_notifications
except ModuleNotFoundError:  # pragma: no cover
    def due_notifications(_board):
        return []

try:
    from services.plugins import PluginContext, PluginRecord, PluginService
except ModuleNotFoundError:  # pragma: no cover
    PluginContext = None  # type: ignore[assignment]
    PluginRecord = None  # type: ignore[assignment]
    PluginService = None  # type: ignore[assignment]

try:
    from services.search import card_matches, filtered_columns, sort_cards
except ModuleNotFoundError:  # pragma: no cover
    card_matches = None  # type: ignore[assignment]
    filtered_columns = None  # type: ignore[assignment]
    sort_cards = None  # type: ignore[assignment]

try:
    from services.sqlite import SCHEMA, SQLiteService
except ModuleNotFoundError:  # pragma: no cover
    SCHEMA = ""
    SQLiteService = None  # type: ignore[assignment]

try:
    from services.storage import StorageService
except ModuleNotFoundError:  # pragma: no cover
    StorageService = None  # type: ignore[assignment]

try:
    from services.templates import BOARD_TEMPLATES, CARD_TEMPLATES, create_board_from_template, create_card_from_template
except ModuleNotFoundError:  # pragma: no cover
    BOARD_TEMPLATES = {}
    CARD_TEMPLATES = {}

    def create_board_from_template(*_args, **_kwargs):
        raise RuntimeError("Brak modułu services.templates")

    def create_card_from_template(*_args, **_kwargs):
        raise RuntimeError("Brak modułu services.templates")

__all__ = [
    "AIResult",
    "BackupService",
    "BOARD_TEMPLATES",
    "CARD_TEMPLATES",
    "ExportService",
    "HistoryService",
    "LocalAIService",
    "PluginContext",
    "PluginRecord",
    "PluginService",
    "SCHEMA",
    "SQLiteService",
    "StorageService",
    "apply_default_automations",
    "card_matches",
    "create_board_from_template",
    "create_card_from_template",
    "due_notifications",
    "filtered_columns",
    "move_card",
    "sort_cards",
]
