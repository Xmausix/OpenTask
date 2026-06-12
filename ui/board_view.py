from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from models.board import Board
from models.card import Card
from models.checklist import ChecklistItem
from models.column import Column
from models.workspace import Workspace
from services import (
    BackupService,
    BOARD_TEMPLATES,
    ExportService,
    HistoryService,
    PluginService,
    SQLiteService,
    StorageService,
    apply_default_automations,
    create_board_from_template,
    due_notifications,
    filtered_columns,
    move_card,
)
from ui.ai_chat import AIChatWindow
from ui.column_view import ColumnView
from ui.dialogs import CardDialog, CardPreviewDialog, LabelManagerDialog, PluginManagerDialog, SettingsDialog, ask_column_name, show_about
from ui.settings import load_settings, save_settings
from ui.themes import THEMES, apply_theme_styles


class BoardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Better Trello 2.7")
        self.geometry("1280x760")
        self.minsize(980, 600)

        self.workspace = Workspace.default()
        self.history = HistoryService(self.workspace)
        self.settings = load_settings(Path(__file__).resolve().parents[1] / "assets" / "settings.json")
        self.palette: dict[str, str] = {}
        self.current_file: Path | None = None
        self.column_views: list[ColumnView] = []
        self.dragged_card_view = None
        self.drag_source_column: Column | None = None
        self.drag_ghost: tk.Toplevel | None = None
        self.last_backup_path: Path | None = None
        self.selected_card_id: str | None = None
        self.ai_chat_window: AIChatWindow | None = None
        self.plugin_hooks: dict[str, list] = {}

        self.search_var = tk.StringVar()
        self.priority_filter_var = tk.StringVar(value="Wszystkie")
        self.label_filter_var = tk.StringVar(value="Wszystkie")
        self.member_filter_var = tk.StringVar()
        self.due_filter_var = tk.StringVar(value="Wszystkie")
        self.sort_var = tk.StringVar(value="Brak")
        self.view_var = tk.StringVar(value="Kanban")
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "light"))

        self._configure_styles()
        self._create_menu()
        self._create_layout()
        self.render_all()
        self.plugin_service = PluginService(Path(__file__).resolve().parents[1] / "plugins")
        self.plugin_service.load_plugins(self)
        self.after(1000, self.check_due_notifications)
        self.after(int(self.settings.get("backup_minutes", 5)) * 60 * 1000, self.auto_backup)

    @property
    def board(self) -> Board:
        board = self.workspace.active_board
        if board is None:
            board = Board.default()
            self.workspace.add_board(board)
        return board

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.palette = apply_theme_styles(self.style, self.settings.get("theme", "light"))

    def _create_menu(self) -> None:
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Nowy workspace", command=self.new_workspace)
        file_menu.add_command(label="Otwórz workspace", command=self.open_workspace, accelerator="Ctrl+O")
        file_menu.add_command(label="Zapisz workspace", command=self.save_workspace, accelerator="Ctrl+S")
        file_menu.add_command(label="Zapisz workspace jako", command=self.save_workspace_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Import CSV", command=self.import_csv)
        file_menu.add_command(label="Eksport JSON", command=lambda: self.export_board("json"))
        file_menu.add_command(label="Eksport CSV", command=lambda: self.export_board("csv"))
        file_menu.add_command(label="Eksport XLSX", command=lambda: self.export_board("xlsx"))
        file_menu.add_command(label="Eksport HTML", command=lambda: self.export_board("html"))
        file_menu.add_command(label="Eksport PDF", command=lambda: self.export_board("pdf"))
        file_menu.add_separator()
        file_menu.add_command(label="Zapisz do SQLite", command=self.save_sqlite)
        file_menu.add_command(label="Otwórz z SQLite", command=self.open_sqlite)
        file_menu.add_separator()
        file_menu.add_command(label="Backup teraz", command=self.manual_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Wyjdź", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        board_menu = tk.Menu(menu_bar, tearoff=False)
        board_menu.add_command(label="Nowa tablica", command=self.new_board, accelerator="Ctrl+N")
        template_menu = tk.Menu(board_menu, tearoff=False)
        for template_name in BOARD_TEMPLATES:
            template_menu.add_command(label=template_name, command=lambda name=template_name: self.new_board_from_template(name))
        board_menu.add_cascade(label="Nowa z szablonu", menu=template_menu)
        board_menu.add_command(label="Kopiuj tablicę", command=self.copy_board)
        board_menu.add_command(label="Archiwizuj tablicę", command=self.archive_board)
        board_menu.add_command(label="Usuń tablicę", command=self.delete_board)
        board_menu.add_separator()
        board_menu.add_command(label="+ Dodaj kolumnę", command=self.add_column)
        board_menu.add_command(label="Zmień nazwę tablicy", command=self.rename_board)
        board_menu.add_command(label="Ulubiona / odznacz", command=self.toggle_favorite_board)
        board_menu.add_separator()
        board_menu.add_command(label="Etykiety tablicy", command=self.manage_labels)
        board_menu.add_command(label="Uruchom automatyzacje", command=self.run_automations)
        menu_bar.add_cascade(label="Board", menu=board_menu)

        view_menu = tk.Menu(menu_bar, tearoff=False)
        for view in ["Kanban", "Table", "Dashboard", "Calendar", "Timeline", "Archive", "Activity"]:
            view_menu.add_radiobutton(label=view, variable=self.view_var, value=view, command=self.render_board)
        theme_menu = tk.Menu(view_menu, tearoff=False)
        for theme_name in THEMES:
            theme_menu.add_radiobutton(label=theme_name, value=theme_name, variable=self.theme_var, command=lambda name=theme_name: self.change_theme(name))
        view_menu.add_separator()
        view_menu.add_cascade(label="Motyw", menu=theme_menu)
        menu_bar.add_cascade(label="View", menu=view_menu)

        self.plugin_menu = tk.Menu(menu_bar, tearoff=False)
        self.plugin_menu.add_command(label="Plugin Manager", command=self.open_plugin_manager)
        self.plugin_menu.add_command(label="Przeładuj pluginy", command=self.reload_plugins)
        self.plugin_menu.add_separator()
        menu_bar.add_cascade(label="Plugins", menu=self.plugin_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="AI Chat", command=self.open_ai_chat)
        help_menu.add_command(label="Ustawienia", command=self.open_settings)
        help_menu.add_command(label="Pomoc", command=self.show_help)
        help_menu.add_command(label="O aplikacji", command=lambda: show_about(self))
        menu_bar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menu_bar)

        self.bind_all("<Control-n>", lambda _event: self.new_board())
        self.bind_all("<Control-o>", lambda _event: self.open_workspace())
        self.bind_all("<Control-s>", lambda _event: self.save_workspace())
        self.bind_all("<Control-Shift-S>", lambda _event: self.save_workspace_as())
        self.bind_all("<Control-f>", lambda _event: self.search_entry.focus_set())
        self.bind_all("<Control-z>", lambda _event: self.undo())
        self.bind_all("<Control-y>", lambda _event: self.redo())

    def _create_layout(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(root, style="Sidebar.TFrame", padding=12, width=230)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        ttk.Label(sidebar, text="", style="Sidebar.TLabel").pack(anchor="w")
        self.workspace_name_var = tk.StringVar()
        ttk.Label(sidebar, textvariable=self.workspace_name_var, style="Sidebar.TLabel").pack(anchor="w", pady=(0, 10))
        self.boards_list = tk.Listbox(sidebar, activestyle="none", bg=self.palette.get("toolbar", "#111827"), fg="#e5e7eb", selectbackground="#2563eb", highlightthickness=0, relief="flat")
        self.boards_list.pack(fill="both", expand=True, pady=(0, 10))
        self.boards_list.bind("<<ListboxSelect>>", self.on_board_select)
        ttk.Button(sidebar, text="+ Tablica", command=self.new_board).pack(fill="x", pady=(0, 6))
        ttk.Button(sidebar, text="★ Ulubiona", command=self.toggle_favorite_board).pack(fill="x", pady=(0, 6))
        ttk.Button(sidebar, text="Kopiuj", command=self.copy_board).pack(fill="x", pady=(0, 6))
        ttk.Button(sidebar, text="Archiwizuj", command=self.archive_board).pack(fill="x")

        main = ttk.Frame(root, style="Board.TFrame")
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(2, weight=1)
        main.columnconfigure(0, weight=1)

        self.toolbar = ttk.Frame(main, style="Toolbar.TFrame", padding=(14, 10))
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.board_title_var = tk.StringVar()
        ttk.Label(self.toolbar, textvariable=self.board_title_var, style="Toolbar.TLabel").pack(side="left")
        ttk.Button(self.toolbar, text="AI Chat", command=self.open_ai_chat).pack(side="right", padx=(8, 0))
        ttk.Button(self.toolbar, text="Zapisz", command=self.save_workspace).pack(side="right", padx=(8, 0))
        ttk.Button(self.toolbar, text="Otwórz", command=self.open_workspace).pack(side="right", padx=(8, 0))
        ttk.Button(self.toolbar, text="Nowa tablica", command=self.new_board).pack(side="right", padx=(8, 0))

        filters = ttk.Frame(main, padding=(14, 8))
        filters.grid(row=1, column=0, sticky="ew")
        filters.columnconfigure(1, weight=1)
        ttk.Label(filters, text="🔍").grid(row=0, column=0, sticky="w")
        self.search_entry = ttk.Entry(filters, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(4, 8))
        ttk.Label(filters, text="Priorytet").grid(row=0, column=2)
        ttk.Combobox(filters, textvariable=self.priority_filter_var, values=["Wszystkie", "high", "medium", "low"], width=10, state="readonly").grid(row=0, column=3, padx=(4, 8))
        ttk.Label(filters, text="Etykieta").grid(row=0, column=4)
        self.label_combo = ttk.Combobox(filters, textvariable=self.label_filter_var, values=["Wszystkie"], width=12, state="readonly")
        self.label_combo.grid(row=0, column=5, padx=(4, 8))
        ttk.Label(filters, text="User").grid(row=0, column=6)
        ttk.Entry(filters, textvariable=self.member_filter_var, width=12).grid(row=0, column=7, padx=(4, 8))
        ttk.Label(filters, text="Termin").grid(row=0, column=8)
        ttk.Combobox(filters, textvariable=self.due_filter_var, values=["Wszystkie", "Po terminie", "Dziś", "Bez terminu", "Archiwum"], width=12, state="readonly").grid(row=0, column=9, padx=(4, 8))
        ttk.Label(filters, text="Sortuj").grid(row=0, column=10)
        ttk.Combobox(filters, textvariable=self.sort_var, values=["Brak", "Termin", "Priorytet", "Data utworzenia", "Alfabetycznie"], width=15, state="readonly").grid(row=0, column=11, padx=(4, 8))
        ttk.Button(filters, text="+ Kolumna", command=self.add_column).grid(row=0, column=12)

        for var in [self.search_var, self.priority_filter_var, self.label_filter_var, self.member_filter_var, self.due_filter_var, self.sort_var]:
            var.trace_add("write", lambda *_args: self.render_board())

        container = ttk.Frame(main, style="Board.TFrame")
        container.grid(row=2, column=0, sticky="nsew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(container, bg=self.palette.get("board_bg", "#f3f4f6"), highlightthickness=0)
        self.h_scroll = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.board_frame = ttk.Frame(self.canvas, style="Board.TFrame", padding=16)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.board_frame, anchor="nw")
        self.board_frame.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.canvas_window, height=event.height))

    def remember(self) -> None:
        self.history.push(self.workspace)

    def undo(self) -> None:
        restored = self.history.undo(self.workspace)
        if restored is None:
            self.status_message("Brak operacji do cofnięcia")
            return
        self.workspace = restored
        self.render_all()

    def redo(self) -> None:
        restored = self.history.redo(self.workspace)
        if restored is None:
            self.status_message("Brak operacji do ponowienia")
            return
        self.workspace = restored
        self.render_all()

    def change_theme(self, theme_name: str) -> None:
        self.settings["theme"] = theme_name
        save_settings(self.settings, Path(__file__).resolve().parents[1] / "assets" / "settings.json")
        self.palette = apply_theme_styles(self.style, theme_name)
        if hasattr(self, "canvas"):
            self.canvas.configure(bg=self.palette.get("board_bg", "#f3f4f6"))
        if hasattr(self, "boards_list"):
            self.boards_list.configure(bg=self.palette.get("toolbar", "#111827"))
        self.render_all()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, self.settings, list(THEMES.keys()))
        self.wait_window(dialog)
        if dialog.result is not None:
            self.settings = dialog.result
            save_settings(self.settings, Path(__file__).resolve().parents[1] / "assets" / "settings.json")
            self.change_theme(self.settings.get("theme", "light"))
            self.status_message("Ustawienia zapisane")

    def manage_labels(self) -> None:
        dialog = LabelManagerDialog(self, self.board.labels)
        self.wait_window(dialog)
        if dialog.result is not None:
            self.remember()
            self.board.labels = dialog.result
            self.board.add_activity("labels_updated", f"Liczba etykiet: {len(dialog.result)}")
            self.render_board()

    def run_automations(self) -> None:
        self.remember()
        changes = apply_default_automations(self.board)
        if changes:
            self.render_board()
            messagebox.showinfo("Automatyzacje", "Zastosowano zmiany:\n" + "\n".join(changes[:20]), parent=self)
        else:
            messagebox.showinfo("Automatyzacje", "Brak zmian do zastosowania.", parent=self)

    def add_plugin_command(self, label: str, command) -> None:
        if hasattr(self, "plugin_menu"):
            self.plugin_menu.add_command(label=label, command=command)

    def register_plugin_hook(self, event_name: str, callback) -> None:
        self.plugin_hooks.setdefault(event_name, []).append(callback)

    def emit_plugin_event(self, event_name: str, **payload) -> None:
        for callback in self.plugin_hooks.get(event_name, []):
            try:
                callback(**payload)
            except Exception as error:
                if hasattr(self, "plugin_service"):
                    self.plugin_service.errors.append(f"hook {event_name}: {error}")

    def open_plugin_manager(self) -> None:
        if not hasattr(self, "plugin_service"):
            messagebox.showinfo("Pluginy", "Plugin service nie został jeszcze uruchomiony.", parent=self)
            return
        PluginManagerDialog(self, self.plugin_service)

    def reload_plugins(self) -> None:
        if not hasattr(self, "plugin_service"):
            return
        self.plugin_hooks.clear()
        # Usuń komendy pluginów i zbuduj menu od nowa.
        self.plugin_menu.delete(0, "end")
        self.plugin_menu.add_command(label="Plugin Manager", command=self.open_plugin_manager)
        self.plugin_menu.add_command(label="Przeładuj pluginy", command=self.reload_plugins)
        self.plugin_menu.add_separator()
        self.plugin_service.load_plugins(self)
        self.status_message(f"Pluginy przeładowane: {len(self.plugin_service.loaded)}")

    def render_all(self) -> None:
        self.render_workspace()
        self.render_board()

    def render_workspace(self) -> None:
        self.workspace_name_var.set(self.workspace.name)
        self.boards_list.delete(0, "end")
        self._board_list_ids = []
        active_id = self.workspace.active_board_id
        for board in self.workspace.visible_boards():
            prefix = "★ " if board.favorite else "  "
            self.boards_list.insert("end", f"{prefix}{board.name}")
            self._board_list_ids.append(board.id)
            if board.id == active_id:
                self.boards_list.selection_set("end")

    def render_board(self) -> None:
        self.board_title_var.set(("★ " if self.board.favorite else "") + self.board.name)
        self.label_combo["values"] = ["Wszystkie"] + sorted({label.name for label in self.board.labels} | {label.name for col in self.board.columns for card in col.cards for label in card.labels})
        for child in self.board_frame.winfo_children():
            child.destroy()
        self.column_views.clear()

        view = self.view_var.get()
        if view == "Table":
            self.render_table_view(); return
        if view == "Dashboard":
            self.render_dashboard_view(); return
        if view == "Calendar":
            self.render_calendar_view(); return
        if view == "Timeline":
            self.render_timeline_view(); return
        if view == "Archive":
            self.render_archive_view(); return
        if view == "Activity":
            self.render_activity_view(); return
        self.render_kanban_view()

    def render_kanban_view(self) -> None:
        display_columns = filtered_columns(self.board, self.search_var.get(), self.priority_filter_var.get(), self.label_filter_var.get(), self.member_filter_var.get(), self.due_filter_var.get(), self.sort_var.get())
        for index, display_column in enumerate(display_columns):
            column_view = ColumnView(
                self.board_frame, display_column, self.add_card, self.rename_column, self.delete_column, self.move_column_left, self.move_column_right,
                self.edit_card, self.preview_card, self.toggle_archive_card, self.duplicate_card, self.delete_card, self.start_drag, self.dragging, self.drop,
            )
            column_view.grid(row=0, column=index, sticky="nsew", padx=(0, 14), pady=0)
            self.board_frame.columnconfigure(index, minsize=270)
            self.column_views.append(column_view)
        ttk.Button(self.board_frame, text="+ Kolumna", command=self.add_column).grid(row=0, column=len(display_columns), sticky="n", padx=(0, 14))

    def render_table_view(self) -> None:
        headers = ["Kolumna", "Zadanie", "Termin", "Priorytet", "Etykiety", "Postęp"]
        for col, header in enumerate(headers):
            ttk.Label(self.board_frame, text=header, font=("TkDefaultFont", 10, "bold")).grid(row=0, column=col, sticky="w", padx=8, pady=4)
        row = 1
        for column in filtered_columns(self.board, self.search_var.get(), self.priority_filter_var.get(), self.label_filter_var.get(), self.member_filter_var.get(), self.due_filter_var.get(), self.sort_var.get()):
            for card in column.cards:
                values = [column.name, card.title, card.due_date or "", card.priority, ", ".join(label.name for label in card.labels), f"{card.checklist_progress}%"]
                for col, value in enumerate(values):
                    ttk.Label(self.board_frame, text=value).grid(row=row, column=col, sticky="w", padx=8, pady=4)
                row += 1

    def render_dashboard_view(self) -> None:
        ttk.Label(self.board_frame, text="Dashboard", font=("TkDefaultFont", 18, "bold")).grid(row=0, column=0, sticky="w")
        for row, column in enumerate(self.board.columns, start=1):
            count = len([card for card in column.cards if not card.archived])
            ttk.Label(self.board_frame, text=f"{column.name}: {count}", font=("TkDefaultFont", 12)).grid(row=row, column=0, sticky="w", pady=4)
        total = sum(len([card for card in column.cards if not card.archived]) for column in self.board.columns)
        done = len([card for column in self.board.columns if "got" in column.name.lower() or "done" in column.name.lower() for card in column.cards if not card.archived])
        percent = round((done / total) * 100) if total else 0
        ttk.Label(self.board_frame, text=f"Progress: {percent}%", font=("TkDefaultFont", 12, "bold")).grid(row=len(self.board.columns)+1, column=0, sticky="w", pady=12)
        canvas = tk.Canvas(self.board_frame, width=420, height=180, bg="#ffffff", highlightthickness=1, highlightbackground="#e5e7eb")
        canvas.grid(row=len(self.board.columns)+2, column=0, sticky="w")
        x = 20
        for column in self.board.columns:
            count = len([card for card in column.cards if not card.archived])
            height = max(4, count * 15)
            canvas.create_rectangle(x, 160 - height, x + 50, 160, fill="#2563eb")
            canvas.create_text(x + 25, 170, text=column.name[:8], anchor="n")
            canvas.create_text(x + 25, 150 - height, text=str(count))
            x += 80

    def render_calendar_view(self) -> None:
        ttk.Label(self.board_frame, text="Calendar — karty z terminem", font=("TkDefaultFont", 18, "bold")).grid(row=0, column=0, sticky="w")
        row = 1
        cards = sorted([card for column in self.board.columns for card in column.cards if card.due_date and not card.archived], key=lambda c: c.due_date or "")
        for card in cards:
            ttk.Label(self.board_frame, text=f"📅 {card.due_date} — {card.title} [{card.priority}]").grid(row=row, column=0, sticky="w", pady=3)
            row += 1

    def render_timeline_view(self) -> None:
        ttk.Label(self.board_frame, text="Timeline / Gantt — uproszczony widok lokalny", font=("TkDefaultFont", 18, "bold")).grid(row=0, column=0, sticky="w")
        row = 1
        for column in self.board.columns:
            for card in column.cards:
                if not card.archived:
                    ttk.Label(self.board_frame, text=f"{card.title:20} {'█' * (3 + len(card.title) % 10)} {card.due_date or ''}").grid(row=row, column=0, sticky="w", pady=3)
                    row += 1

    def render_archive_view(self) -> None:
        ttk.Label(self.board_frame, text="Archive — zarchiwizowane karty", font=("TkDefaultFont", 18, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))
        row = 1
        archived_cards = [(column, card) for column in self.board.columns for card in column.cards if card.archived]
        if not archived_cards:
            ttk.Label(self.board_frame, text="Archiwum jest puste.").grid(row=row, column=0, sticky="w")
            return
        for column, card in archived_cards:
            ttk.Label(self.board_frame, text=column.name).grid(row=row, column=0, sticky="w", padx=6, pady=3)
            ttk.Label(self.board_frame, text=card.title).grid(row=row, column=1, sticky="w", padx=6, pady=3)
            ttk.Label(self.board_frame, text=card.priority).grid(row=row, column=2, sticky="w", padx=6, pady=3)
            ttk.Button(self.board_frame, text="Przywróć", command=lambda c=card: self.toggle_archive_card(c)).grid(row=row, column=3, padx=6, pady=3)
            ttk.Button(self.board_frame, text="Usuń", command=lambda c=card: self.delete_card(c)).grid(row=row, column=4, padx=6, pady=3)
            row += 1

    def render_activity_view(self) -> None:
        ttk.Label(self.board_frame, text="Activity", font=("TkDefaultFont", 18, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        if not self.board.activities:
            ttk.Label(self.board_frame, text="Brak aktywności.").grid(row=1, column=0, sticky="w")
            return
        for row, activity in enumerate(self.board.activities[:200], start=1):
            ttk.Label(self.board_frame, text=activity.created_at).grid(row=row, column=0, sticky="w", padx=6, pady=3)
            ttk.Label(self.board_frame, text=activity.action).grid(row=row, column=1, sticky="w", padx=6, pady=3)
            ttk.Label(self.board_frame, text=activity.details).grid(row=row, column=2, sticky="w", padx=6, pady=3)

    def all_cards(self) -> list[Card]:
        return [card for column in self.board.columns for card in column.cards]

    def all_cards_except(self, card_id: str | None = None) -> list[Card]:
        return [card for card in self.all_cards() if card.id != card_id and not card.archived]

    def get_selected_card(self) -> Card | None:
        if not self.selected_card_id:
            return None
        _column, card = self.get_card_location(self.selected_card_id)
        return card

    def preview_card(self, card: Card) -> None:
        self.selected_card_id = card.id
        CardPreviewDialog(self, card)

    def open_ai_chat(self) -> None:
        if self.ai_chat_window is not None and self.ai_chat_window.winfo_exists():
            self.ai_chat_window.lift()
            return
        self.ai_chat_window = AIChatWindow(self, lambda: self.board, self.get_selected_card, self.apply_ai_checklist)

    def apply_ai_checklist(self, card: Card, items: list[str]) -> None:
        _column, actual = self.get_card_location(card.id)
        if actual is None:
            return
        existing = {item.text.strip().lower() for item in actual.checklist}
        new_items = [ChecklistItem(text=item) for item in items if item.strip().lower() not in existing]
        if not new_items:
            return
        self.remember()
        actual.checklist.extend(new_items)
        actual.touch()
        self.board.add_activity("ai_checklist_added", f"{actual.title}: +{len(new_items)} pozycji")
        self.render_board()

    def get_actual_column(self, column: Column) -> Column | None:
        return next((item for item in self.board.columns if item.id == column.id), None)

    def get_card_location(self, card_id: str) -> tuple[Column, Card] | tuple[None, None]:
        for column in self.board.columns:
            for card in column.cards:
                if card.id == card_id:
                    return column, card
        return None, None

    def is_done_column(self, column: Column) -> bool:
        name = column.name.lower()
        return "done" in name or "got" in name or "ukoń" in name

    def dependencies_are_done(self, card: Card) -> bool:
        if not card.dependencies:
            return True
        done_card_ids = {
            item.id
            for column in self.board.columns
            if self.is_done_column(column)
            for item in column.cards
            if not item.archived
        }
        return all(dependency_id in done_card_ids for dependency_id in card.dependencies)

    def on_board_select(self, _event=None) -> None:
        selection = self.boards_list.curselection()
        if not selection:
            return
        self.workspace.active_board_id = self._board_list_ids[selection[0]]
        self.render_board()

    def new_workspace(self) -> None:
        name = ask_column_name(self, "Nazwa workspace:", "")
        if name:
            self.workspace = Workspace(name=name, boards=[])
            self.workspace.add_board(Board.default())
            self.history.reset(self.workspace)
            self.current_file = None
            self.render_all()

    def new_board(self) -> None:
        name = ask_column_name(self, "Nazwa nowej tablicy:", "Projekt WWW")
        if not name:
            return
        self.remember()
        board = Board(name=name, columns=[Column(name="Backlog", emoji="📥"), Column(name="Sprint", emoji="🚀"), Column(name="Review", emoji="🔍"), Column(name="Done", emoji="✅")])
        self.workspace.add_board(board)
        self.render_all()

    def new_board_from_template(self, template_name: str) -> None:
        name = ask_column_name(self, f"Nazwa tablicy z szablonu {template_name}:", template_name)
        if not name:
            return
        self.remember()
        self.workspace.add_board(create_board_from_template(name, template_name))
        self.render_all()

    def rename_board(self) -> None:
        name = ask_column_name(self, "Nowa nazwa tablicy:", self.board.name)
        if name:
            self.remember()
            self.board.name = name
            self.board.add_activity("board_renamed", name)
            self.render_all()

    def toggle_favorite_board(self) -> None:
        self.remember()
        self.board.favorite = not self.board.favorite
        self.board.add_activity("board_favorite", "Oznaczono jako ulubioną" if self.board.favorite else "Usunięto z ulubionych")
        self.render_all()

    def copy_board(self) -> None:
        self.remember()
        self.workspace.add_board(self.board.clone())
        self.render_all()

    def archive_board(self) -> None:
        if len([b for b in self.workspace.boards if not b.archived]) <= 1:
            messagebox.showwarning("Archiwum", "Workspace musi mieć przynajmniej jedną aktywną tablicę.", parent=self); return
        self.remember()
        self.board.archived = True
        self.workspace.active_board_id = next((b.id for b in self.workspace.boards if not b.archived), None)
        self.render_all()

    def delete_board(self) -> None:
        if len(self.workspace.boards) <= 1:
            messagebox.showwarning("Usuń", "Nie można usunąć ostatniej tablicy.", parent=self); return
        if messagebox.askyesno("Usuń tablicę", f"Usunąć „{self.board.name}” na stałe?", parent=self):
            self.remember()
            current = self.board
            self.workspace.boards.remove(current)
            self.workspace.active_board_id = self.workspace.boards[0].id
            self.render_all()

    def add_column(self) -> None:
        name = ask_column_name(self, "Nazwa kolumny, opcjonalnie z emoji:", "🚀 Sprint")
        if name:
            self.remember()
            parts = name.split(maxsplit=1)
            emoji, col_name = (parts[0], parts[1]) if len(parts) == 2 and not parts[0].isalnum() else ("", name)
            self.board.columns.append(Column(name=col_name, emoji=emoji))
            self.board.add_activity("column_added", col_name)
            self.render_board()

    def rename_column(self, column: Column) -> None:
        actual = self.get_actual_column(column)
        if not actual: return
        name = ask_column_name(self, "Nowa nazwa kolumny:", f"{actual.emoji} {actual.name}" if actual.emoji else actual.name)
        if name:
            self.remember()
            parts = name.split(maxsplit=1)
            actual.emoji, actual.name = ((parts[0], parts[1]) if len(parts) == 2 and not parts[0].isalnum() else ("", name))
            self.board.add_activity("column_renamed", actual.name)
            self.render_board()

    def delete_column(self, column: Column) -> None:
        actual = self.get_actual_column(column)
        if not actual: return
        if len(self.board.columns) <= 1:
            messagebox.showwarning("Nie można usunąć", "Tablica musi mieć przynajmniej jedną kolumnę.", parent=self); return
        if actual.cards and not messagebox.askyesno("Usuń kolumnę", f"Usunąć „{actual.name}” razem z kartami?", parent=self):
            return
        self.remember()
        self.board.columns.remove(actual)
        self.board.add_activity("column_deleted", actual.name)
        self.render_board()

    def move_column_left(self, column: Column) -> None:
        actual = self.get_actual_column(column)
        if actual:
            idx = self.board.columns.index(actual)
            if idx > 0:
                self.remember()
                self.board.columns[idx - 1], self.board.columns[idx] = self.board.columns[idx], self.board.columns[idx - 1]
                self.board.add_activity("column_moved", actual.name)
                self.render_board()

    def move_column_right(self, column: Column) -> None:
        actual = self.get_actual_column(column)
        if actual:
            idx = self.board.columns.index(actual)
            if idx < len(self.board.columns) - 1:
                self.remember()
                self.board.columns[idx + 1], self.board.columns[idx] = self.board.columns[idx], self.board.columns[idx + 1]
                self.board.add_activity("column_moved", actual.name)
                self.render_board()

    def add_card(self, column: Column) -> None:
        actual = self.get_actual_column(column)
        if not actual: return
        dialog = CardDialog(self, title="Dodaj kartę", available_cards=self.all_cards_except())
        self.wait_window(dialog)
        if dialog.result is not None:
            self.remember()
            actual.cards.append(dialog.result)
            self.board.add_activity("card_added", dialog.result.title)
            self.emit_plugin_event("card_added", board=self.board, column=actual, card=dialog.result)
            self.render_board()

    def edit_card(self, card: Card) -> None:
        self.selected_card_id = card.id
        source, actual = self.get_card_location(card.id)
        if not actual: return
        self.remember()
        dialog = CardDialog(self, actual, title="Edytuj kartę", available_cards=self.all_cards_except(actual.id))
        self.wait_window(dialog)
        if dialog.result is not None:
            self.board.add_activity("card_updated", dialog.result.title)
            self.emit_plugin_event("card_updated", board=self.board, card=dialog.result)
            self.render_board()

    def toggle_archive_card(self, card: Card) -> None:
        _source, actual = self.get_card_location(card.id)
        if actual:
            self.remember()
            actual.archived = not actual.archived
            actual.touch()
            event_name = "card_restored" if not actual.archived else "card_archived"
            self.board.add_activity(event_name, actual.title)
            self.emit_plugin_event(event_name, board=self.board, card=actual)
            self.render_board()

    def delete_card(self, card: Card) -> None:
        source, actual = self.get_card_location(card.id)
        if source and actual and messagebox.askyesno("Usuń kartę", f"Usunąć „{actual.title}” na stałe?", parent=self):
            self.remember()
            source.cards.remove(actual)
            self.board.add_activity("card_deleted", actual.title)
            self.emit_plugin_event("card_deleted", board=self.board, card=actual)
            self.render_board()

    def duplicate_card(self, card: Card) -> None:
        source, actual = self.get_card_location(card.id)
        if source and actual:
            self.remember()
            copied = deepcopy(actual)
            from uuid import uuid4
            copied.id = str(uuid4())
            copied.title = f"{actual.title} — kopia"
            copied.archived = False
            copied.touch()
            source.cards.append(copied)
            self.board.add_activity("card_copied", copied.title)
            self.emit_plugin_event("card_copied", board=self.board, source_card=actual, card=copied)
            self.render_board()

    def start_drag(self, card_view, event) -> None:
        self.dragged_card_view = card_view
        self.drag_source_column, _actual = self.get_card_location(card_view.card.id)
        self._show_drag_ghost(card_view.card.title, event.x_root, event.y_root)

    def dragging(self, card_view, event) -> None:
        if self.dragged_card_view is None:
            self.start_drag(card_view, event)
        self._move_drag_ghost(event.x_root, event.y_root)
        self._highlight_target(event.x_root, event.y_root)

    def drop(self, card_view, event) -> None:
        target = self.detect_column(event.x_root, event.y_root)
        source = self.drag_source_column
        _col, actual_card = self.get_card_location(card_view.card.id)
        self._destroy_drag_ghost(); self._clear_highlights()
        if source is not None and target is not None and target is not source and actual_card is not None:
            if self.is_done_column(target) and not self.dependencies_are_done(actual_card):
                messagebox.showwarning("Zależności", "Nie można przenieść karty do Done/Gotowe, dopóki zależności nie są ukończone.", parent=self)
            else:
                self.remember()
                move_card(actual_card, source, target)
                self.board.add_activity("card_moved", f"{actual_card.title}: {source.name} → {target.name}")
                self.emit_plugin_event("card_moved", board=self.board, card=actual_card, source=source, target=target)
                self.render_board()
        self.dragged_card_view = None; self.drag_source_column = None

    def detect_column(self, x_root: int, y_root: int) -> Column | None:
        for view in self.column_views:
            if view.contains_screen_point(x_root, y_root):
                return self.get_actual_column(view.column)
        return None

    def _show_drag_ghost(self, title: str, x_root: int, y_root: int) -> None:
        self._destroy_drag_ghost()
        self.drag_ghost = tk.Toplevel(self); self.drag_ghost.overrideredirect(True); self.drag_ghost.attributes("-topmost", True)
        tk.Label(self.drag_ghost, text=f"↕ {title}", bg="#111827", fg="#ffffff", padx=10, pady=6).pack()
        self._move_drag_ghost(x_root, y_root)

    def _move_drag_ghost(self, x_root: int, y_root: int) -> None:
        if self.drag_ghost is not None: self.drag_ghost.geometry(f"+{x_root + 12}+{y_root + 12}")

    def _destroy_drag_ghost(self) -> None:
        if self.drag_ghost is not None:
            try: self.drag_ghost.destroy()
            except tk.TclError: pass
            self.drag_ghost = None

    def _highlight_target(self, x_root: int, y_root: int) -> None:
        target = self.detect_column(x_root, y_root)
        for view in self.column_views:
            view.configure(style="ColumnHighlight.TFrame" if self.get_actual_column(view.column) is target else "Column.TFrame")

    def _clear_highlights(self) -> None:
        for view in self.column_views: view.configure(style="Column.TFrame")

    def save_workspace(self) -> None:
        if self.current_file is None:
            self.save_workspace_as(); return
        try:
            StorageService.save_workspace(self.workspace, self.current_file)
            self.emit_plugin_event("workspace_saved", workspace=self.workspace, path=self.current_file)
        except OSError as error:
            messagebox.showerror("Błąd zapisu", str(error), parent=self)

    def save_workspace_as(self) -> None:
        file_path = filedialog.asksaveasfilename(parent=self, title="Zapisz workspace jako", defaultextension=".json", filetypes=[("JSON", "*.json"), ("Wszystkie pliki", "*.*")], initialfile="workspace.json")
        if file_path:
            self.current_file = Path(file_path)
            self.save_workspace()

    def open_workspace(self) -> None:
        file_path = filedialog.askopenfilename(parent=self, title="Otwórz workspace lub tablicę", filetypes=[("JSON", "*.json"), ("Wszystkie pliki", "*.*")])
        if not file_path: return
        try:
            self.workspace = StorageService.load_workspace(file_path)
            self.history.reset(self.workspace)
            self.current_file = Path(file_path)
            self.render_all()
        except (OSError, ValueError) as error:
            messagebox.showerror("Błąd odczytu", str(error), parent=self)

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Import CSV", filetypes=[("CSV", "*.csv"), ("Wszystkie pliki", "*.*")])
        if not path:
            return
        try:
            self.remember()
            added = ExportService.import_csv_to_board(self.board, path)
            self.render_board()
            messagebox.showinfo("Import CSV", f"Zaimportowano {added} kart.", parent=self)
        except (OSError, ValueError) as error:
            messagebox.showerror("Import CSV", str(error), parent=self)

    def export_board(self, kind: str) -> None:
        ext = kind
        path = filedialog.asksaveasfilename(parent=self, title=f"Eksport {kind.upper()}", defaultextension=f".{ext}", filetypes=[(kind.upper(), f"*.{ext}"), ("Wszystkie pliki", "*.*")], initialfile=f"{self.board.name.replace(' ', '_').lower()}.{ext}")
        if not path: return
        try:
            if kind == "json": ExportService.export_json(self.board, path)
            elif kind == "csv": ExportService.export_csv(self.board, path)
            elif kind == "xlsx": ExportService.export_xlsx(self.board, path)
            elif kind == "html": ExportService.export_html(self.board, path)
            elif kind == "pdf": ExportService.export_pdf_text_fallback(self.board, path)
            messagebox.showinfo("Eksport", f"Wyeksportowano: {path}", parent=self)
        except OSError as error:
            messagebox.showerror("Eksport", str(error), parent=self)

    def save_sqlite(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, title="Zapisz SQLite", defaultextension=".sqlite3", filetypes=[("SQLite", "*.sqlite3 *.db"), ("Wszystkie pliki", "*.*")], initialfile="kanban.sqlite3")
        if not path:
            return
        try:
            SQLiteService(path).save_workspace(self.workspace)
            messagebox.showinfo("SQLite", f"Zapisano bazę:\n{path}", parent=self)
        except OSError as error:
            messagebox.showerror("SQLite", str(error), parent=self)

    def open_sqlite(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Otwórz SQLite", filetypes=[("SQLite", "*.sqlite3 *.db"), ("Wszystkie pliki", "*.*")])
        if not path:
            return
        try:
            self.workspace = SQLiteService(path).load_workspace()
            self.history.reset(self.workspace)
            self.render_all()
            messagebox.showinfo("SQLite", f"Otworzono bazę:\n{path}", parent=self)
        except (OSError, ValueError) as error:
            messagebox.showerror("SQLite", str(error), parent=self)

    def manual_backup(self) -> None:
        self.last_backup_path = BackupService(Path(__file__).resolve().parents[1] / "backups").create_backup(self.workspace)
        messagebox.showinfo("Backup", f"Utworzono backup:\n{self.last_backup_path}", parent=self)

    def auto_backup(self) -> None:
        try:
            self.last_backup_path = BackupService(Path(__file__).resolve().parents[1] / "backups").create_backup(self.workspace)
        finally:
            self.after(int(self.settings.get("backup_minutes", 5)) * 60 * 1000, self.auto_backup)

    def check_due_notifications(self) -> None:
        messages = due_notifications(self.board)
        if messages:
            self.status_message("  |  ".join(messages[:3]))

    def status_message(self, text: str) -> None:
        old = self.board_title_var.get()
        self.board_title_var.set(f"{old}    ⚠ {text}")
        self.after(8000, lambda: self.board_title_var.set(("★ " if self.board.favorite else "") + self.board.name))

    def show_help(self) -> None:
        messagebox.showinfo(
            "Pomoc",
            "Skróty: Ctrl+N nowa tablica, Ctrl+S zapis, Ctrl+O otwórz, Ctrl+F szukaj.\n\n"
            "Karty: dwuklik otwiera edycję, prawy klik pokazuje akcje, przeciągnij kartę do innej kolumny.\n"
            "Kolumny można przesuwać w menu ⋯. Widoki Archive i Activity pokazują archiwum oraz historię zmian.",
            parent=self,
        )
