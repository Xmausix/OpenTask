from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


HookCallback = Callable[..., None]


@dataclass
class PluginRecord:
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = "Local"
    path: str = ""
    enabled: bool = True
    module_name: str = ""
    commands: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "path": self.path,
            "enabled": self.enabled,
            "module_name": self.module_name,
            "commands": self.commands,
            "hooks": self.hooks,
        }


class PluginContext:
    """API przekazywane pluginom.

    Plugin może korzystać tylko z jawnie udostępnionych metod, zamiast grzebać
    bezpośrednio w całej aplikacji. Dla kompatybilności nadal można użyć
    register(app), ale rekomendowane jest register(context).
    """

    def __init__(self, app: Any, record: PluginRecord) -> None:
        self.app = app
        self.record = record

    @property
    def board(self):
        return self.app.board

    @property
    def workspace(self):
        return self.app.workspace

    def add_command(self, label: str, callback: Callable[[], None]) -> None:
        self.record.commands.append(label)
        self.app.add_plugin_command(label, callback)

    def add_hook(self, event_name: str, callback: HookCallback) -> None:
        self.record.hooks.append(event_name)
        self.app.register_plugin_hook(event_name, callback)

    def status(self, message: str) -> None:
        self.app.status_message(message)

    def refresh(self) -> None:
        self.app.render_all()

    def selected_card(self):
        return self.app.get_selected_card()

    def open_ai_chat(self) -> None:
        self.app.open_ai_chat()


class PluginService:
    """Lokalny system pluginów Better Trello.

    Obsługiwane formaty pluginu:

    1. Nowy format:

        PLUGIN = {
            "name": "My Plugin",
            "version": "1.0.0",
            "description": "...",
            "author": "...",
        }

        def register(context):
            context.add_command("Akcja", lambda: ...)
            context.add_hook("card_added", lambda card=None, **kw: ...)

    2. Stary format kompatybilny:

        def register(app):
            app.add_plugin_command("Akcja", lambda: ...)
    """

    def __init__(self, plugins_dir: str | Path = "plugins") -> None:
        self.plugins_dir = Path(plugins_dir)
        self.records: list[PluginRecord] = []
        self.modules: list[ModuleType] = []
        self.errors: list[str] = []

    @property
    def loaded(self) -> list[str]:
        return [record.name for record in self.records if record.enabled]

    def reset(self) -> None:
        self.records.clear()
        self.modules.clear()
        self.errors.clear()

    def load_plugins(self, app: Any) -> list[ModuleType]:
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.reset()
        modules: list[ModuleType] = []
        for path in sorted(self.plugins_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            record = PluginRecord(name=path.stem, path=str(path), module_name=f"better_trello_plugin_{path.stem}")
            try:
                spec = importlib.util.spec_from_file_location(record.module_name, path)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                metadata = getattr(module, "PLUGIN", {}) or {}
                record.name = metadata.get("name", record.name)
                record.version = metadata.get("version", record.version)
                record.description = metadata.get("description", record.description)
                record.author = metadata.get("author", record.author)
                context = PluginContext(app, record)
                if hasattr(module, "register"):
                    try:
                        module.register(context)
                    except AttributeError:
                        # Kompatybilność z pluginami register(app)
                        module.register(app)
                self.records.append(record)
                self.modules.append(module)
                modules.append(module)
            except Exception as error:
                record.enabled = False
                self.records.append(record)
                self.errors.append(f"{path.name}: {error}")
        return modules

    def summary(self) -> str:
        lines = ["Pluginy Better Trello", ""]
        if not self.records:
            lines.append("Brak pluginów.")
        for record in self.records:
            status = "ON" if record.enabled else "ERROR"
            lines.append(f"[{status}] {record.name} {record.version}")
            if record.description:
                lines.append(f"  {record.description}")
            if record.commands:
                lines.append("  Komendy: " + ", ".join(record.commands))
            if record.hooks:
                lines.append("  Hooki: " + ", ".join(record.hooks))
        if self.errors:
            lines.append("\nBłędy:")
            lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)
