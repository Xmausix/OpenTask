from __future__ import annotations

import json
from pathlib import Path


DEFAULT_SETTINGS = {"theme": "light", "backup_minutes": 5, "notifications": True}


def load_settings(path: str | Path = "assets/settings.json") -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return DEFAULT_SETTINGS.copy()
    return {**DEFAULT_SETTINGS, **json.loads(file_path.read_text(encoding="utf-8"))}


def save_settings(settings: dict, path: str | Path = "assets/settings.json") -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps({**DEFAULT_SETTINGS, **settings}, ensure_ascii=False, indent=2), encoding="utf-8")
