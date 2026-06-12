from __future__ import annotations

from tkinter import ttk


THEMES: dict[str, dict[str, str]] = {
    "light": {
        "sidebar": "#0f172a",
        "toolbar": "#111827",
        "board_bg": "#f3f4f6",
        "column_bg": "#ffffff",
        "column_highlight": "#e0f2fe",
        "text": "#111827",
        "muted": "#374151",
    },
    "dark": {
        "sidebar": "#020617",
        "toolbar": "#020617",
        "board_bg": "#111827",
        "column_bg": "#1f2937",
        "column_highlight": "#1e3a8a",
        "text": "#f9fafb",
        "muted": "#d1d5db",
    },
    "blue": {
        "sidebar": "#0c4a6e",
        "toolbar": "#075985",
        "board_bg": "#e0f2fe",
        "column_bg": "#f0f9ff",
        "column_highlight": "#bae6fd",
        "text": "#082f49",
        "muted": "#155e75",
    },
    "github_dark": {
        "sidebar": "#0d1117",
        "toolbar": "#161b22",
        "board_bg": "#0d1117",
        "column_bg": "#161b22",
        "column_highlight": "#1f6feb",
        "text": "#c9d1d9",
        "muted": "#8b949e",
    },
    "dracula": {
        "sidebar": "#282a36",
        "toolbar": "#44475a",
        "board_bg": "#282a36",
        "column_bg": "#44475a",
        "column_highlight": "#6272a4",
        "text": "#f8f8f2",
        "muted": "#bd93f9",
    },
}


def get_theme(name: str) -> dict[str, str]:
    return THEMES.get(name, THEMES["light"])


def apply_theme_styles(style: ttk.Style, theme_name: str) -> dict[str, str]:
    palette = get_theme(theme_name)
    style.configure("Sidebar.TFrame", background=palette["sidebar"])
    style.configure("Sidebar.TLabel", background=palette["sidebar"], foreground="#e5e7eb", font=("TkDefaultFont", 11, "bold"))
    style.configure("Toolbar.TFrame", background=palette["toolbar"])
    style.configure("Toolbar.TLabel", background=palette["toolbar"], foreground="#ffffff", font=("TkDefaultFont", 12, "bold"))
    style.configure("Board.TFrame", background=palette["board_bg"])
    style.configure("Column.TFrame", background=palette["column_bg"], relief="solid", borderwidth=1)
    style.configure("ColumnHighlight.TFrame", background=palette["column_highlight"], relief="solid", borderwidth=2)
    style.configure("ColumnHeader.TFrame", background=palette["column_bg"])
    style.configure("ColumnBody.TFrame", background=palette["column_bg"])
    style.configure("ColumnTitle.TLabel", background=palette["column_bg"], foreground=palette["text"], font=("TkDefaultFont", 11, "bold"))
    return palette
