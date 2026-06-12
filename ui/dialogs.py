from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

# Pozwala uruchomić plik bezpośrednio z IDE jako `python ui/dialogs.py`.
# Normalnie aplikację uruchamiamy przez `python main.py` z katalogu projektu.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.attachment import Attachment
from models.card import Card
from models.checklist import ChecklistItem
from models.comment import Comment
from models.label import Label
from services.templates import CARD_TEMPLATES, create_card_from_template


PRIORITIES = ("low", "medium", "high")
LABEL_PRESETS = {
    "Backend": "#22c55e",
    "API": "#3b82f6",
    "Bug": "#a855f7",
    "Critical": "#ef4444",
    "Frontend": "#f59e0b",
    "Docs": "#64748b",
}


class CardDialog(tk.Toplevel):
    """Popup dodawania/edycji karty w stylu Trello."""

    def __init__(self, master: tk.Misc, card: Card | None = None, title: str = "Karta", available_cards: list[Card] | None = None) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("620x780")
        self.minsize(560, 620)
        self.transient(master)
        self.grab_set()
        self.result: Card | None = None
        self.card = card
        self.available_cards = available_cards or []

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="Tytuł").grid(row=0, column=0, sticky="w")
        template_frame = ttk.Frame(container)
        template_frame.grid(row=0, column=1, sticky="e")
        ttk.Label(template_frame, text="Szablon").pack(side="left", padx=(0, 4))
        self.template_var = tk.StringVar(value="")
        ttk.Combobox(template_frame, textvariable=self.template_var, values=[""] + sorted(CARD_TEMPLATES), width=16, state="readonly").pack(side="left", padx=(0, 4))
        ttk.Button(template_frame, text="Wczytaj", command=self.apply_template).pack(side="left")
        self.title_entry = ttk.Entry(container)
        self.title_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(container, text="Opis").grid(row=2, column=0, sticky="w")
        self.description_text = tk.Text(container, height=4, wrap="word")
        self.description_text.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(container, text="Priorytet").grid(row=4, column=0, sticky="w")
        self.priority_var = tk.StringVar(value="medium")
        priority_frame = ttk.Frame(container)
        priority_frame.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 8))
        for priority in PRIORITIES:
            ttk.Radiobutton(priority_frame, text=priority.capitalize(), variable=self.priority_var, value=priority).pack(side="left", padx=(0, 12))

        ttk.Label(container, text="Termin YYYY-MM-DD").grid(row=6, column=0, sticky="w")
        self.due_entry = ttk.Entry(container)
        self.due_entry.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(container, text="Członkowie, po przecinku").grid(row=8, column=0, sticky="w")
        self.members_entry = ttk.Entry(container)
        self.members_entry.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(container, text="Etykiety").grid(row=10, column=0, sticky="w")
        self.label_vars: dict[str, tk.BooleanVar] = {}
        labels_frame = ttk.Frame(container)
        labels_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        for index, name in enumerate(LABEL_PRESETS):
            var = tk.BooleanVar(value=False)
            self.label_vars[name] = var
            ttk.Checkbutton(labels_frame, text=name, variable=var).grid(row=index // 3, column=index % 3, sticky="w", padx=(0, 12))

        ttk.Label(container, text="Checklisty, jedna pozycja na linię. Zaznacz wykonane prefiksem [x]").grid(row=12, column=0, columnspan=2, sticky="w")
        self.checklist_text = tk.Text(container, height=5, wrap="word")
        self.checklist_text.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(container, text="Komentarze, jeden komentarz na linię").grid(row=14, column=0, columnspan=2, sticky="w")
        self.comments_text = tk.Text(container, height=4, wrap="word")
        self.comments_text.grid(row=15, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        attachments_frame = ttk.Frame(container)
        attachments_frame.grid(row=16, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        attachments_frame.columnconfigure(0, weight=1)
        ttk.Label(attachments_frame, text="Załączniki").grid(row=0, column=0, sticky="w")
        ttk.Button(attachments_frame, text="+ Pliki", command=self.add_attachments).grid(row=0, column=1, sticky="e")
        self.attachments_list = tk.Listbox(attachments_frame, height=3)
        self.attachments_list.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.attachments: list[Attachment] = []

        ttk.Label(container, text="Kolor okładki, np. #93c5fd").grid(row=17, column=0, sticky="w")
        self.cover_entry = ttk.Entry(container)
        self.cover_entry.grid(row=18, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(container, text="Zależności — wybierz karty, które muszą być ukończone wcześniej").grid(row=19, column=0, columnspan=2, sticky="w")
        self.dependencies_list = tk.Listbox(container, height=4, selectmode="multiple")
        self.dependencies_list.grid(row=20, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.dependency_ids: list[str] = []
        for dep_card in self.available_cards:
            self.dependency_ids.append(dep_card.id)
            self.dependencies_list.insert("end", f"{dep_card.title}  [{dep_card.id[:8]}]")

        button_frame = ttk.Frame(container)
        button_frame.grid(row=21, column=0, columnspan=2, sticky="e")
        ttk.Button(button_frame, text="Anuluj", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(button_frame, text="Zapisz", command=self.on_save).pack(side="right")

        self.bind("<Escape>", lambda _event: self.destroy())
        self._fill(card)
        self.title_entry.focus_set()

    def apply_template(self) -> None:
        template_name = self.template_var.get()
        if not template_name:
            return
        template_card = create_card_from_template(template_name)
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, template_card.title)
        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", template_card.description)
        self.priority_var.set(template_card.priority)
        for var in self.label_vars.values():
            var.set(False)
        for label in template_card.labels:
            if label.name in self.label_vars:
                self.label_vars[label.name].set(True)
        self.checklist_text.delete("1.0", "end")
        self.checklist_text.insert("1.0", "\n".join(f"[ ] {item.text}" for item in template_card.checklist))

    def _fill(self, card: Card | None) -> None:
        if not card:
            return
        self.title_entry.insert(0, card.title)
        self.description_text.insert("1.0", card.description)
        self.priority_var.set(card.priority)
        if card.due_date:
            self.due_entry.insert(0, card.due_date)
        self.members_entry.insert(0, ", ".join(card.members))
        for label in card.labels:
            if label.name not in self.label_vars:
                self.label_vars[label.name] = tk.BooleanVar(value=True)
            else:
                self.label_vars[label.name].set(True)
        checklist_lines = []
        for item in card.checklist:
            checklist_lines.append(f"[x] {item.text}" if item.done else f"[ ] {item.text}")
        self.checklist_text.insert("1.0", "\n".join(checklist_lines))
        self.comments_text.insert("1.0", "\n".join(comment.text for comment in card.comments))
        self.attachments = list(card.attachments)
        for attachment in self.attachments:
            self.attachments_list.insert("end", f"📎 {attachment.name or Path(attachment.path).name}")
        self.cover_entry.insert(0, card.cover_color)
        for index, dependency_id in enumerate(self.dependency_ids):
            if dependency_id in card.dependencies:
                self.dependencies_list.selection_set(index)

    def add_attachments(self) -> None:
        paths = filedialog.askopenfilenames(
            parent=self,
            title="Dodaj załączniki",
            filetypes=[
                ("Obsługiwane", "*.pdf *.docx *.jpg *.jpeg *.png *.zip"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        for path in paths:
            attachment = Attachment(path=path)
            self.attachments.append(attachment)
            self.attachments_list.insert("end", f"📎 {attachment.name}")

    def on_save(self) -> None:
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Brak tytułu", "Podaj tytuł karty.", parent=self)
            return
        due_date = self.due_entry.get().strip() or None
        if due_date and len(due_date) != 10:
            messagebox.showwarning("Termin", "Podaj termin w formacie YYYY-MM-DD albo zostaw puste.", parent=self)
            return
        card = self.card or Card()
        card.title = title
        card.description = self.description_text.get("1.0", "end").strip()
        card.priority = self.priority_var.get()
        card.due_date = due_date
        card.members = [member.strip() for member in self.members_entry.get().split(",") if member.strip()]
        card.labels = [Label(name=name, color=LABEL_PRESETS.get(name, "#3b82f6")) for name, var in self.label_vars.items() if var.get()]
        card.checklist = []
        for line in self.checklist_text.get("1.0", "end").splitlines():
            line = line.strip()
            if not line:
                continue
            done = line.lower().startswith("[x]") or line.startswith("☑")
            text = line.replace("[x]", "", 1).replace("[X]", "", 1).replace("[ ]", "", 1).replace("☑", "", 1).replace("☐", "", 1).strip()
            card.checklist.append(ChecklistItem(text=text, done=done))
        existing_comments = [comment.text for comment in card.comments]
        new_comments = []
        for line in self.comments_text.get("1.0", "end").splitlines():
            text = line.strip()
            if text and text not in existing_comments:
                new_comments.append(Comment(text=text))
        card.comments.extend(new_comments)
        card.attachments = self.attachments
        card.cover_color = self.cover_entry.get().strip()
        card.dependencies = [self.dependency_ids[index] for index in self.dependencies_list.curselection()]
        card.touch()
        self.result = card
        self.destroy()


def ask_column_name(master: tk.Misc, prompt: str, initialvalue: str = "") -> str | None:
    value = simpledialog.askstring("Nazwa", prompt, initialvalue=initialvalue, parent=master)
    if value is None:
        return None
    value = value.strip()
    return value or None


class PluginManagerDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, plugin_service) -> None:
        super().__init__(master)
        self.title("Plugin Manager")
        self.geometry("680x520")
        self.minsize(560, 420)
        self.transient(master)

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Pluginy Better Trello", font=("TkDefaultFont", 14, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        text = tk.Text(frame, wrap="word")
        text.grid(row=1, column=0, sticky="nsew")
        text.insert("1.0", plugin_service.summary())
        text.configure(state="disabled")

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="Zamknij", command=self.destroy).pack(side="right")


class CardPreviewDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, card: Card) -> None:
        super().__init__(master)
        self.title(f"Podgląd taska — {card.title}")
        self.geometry("560x640")
        self.minsize(480, 420)
        self.transient(master)

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text=card.title, font=("TkDefaultFont", 16, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        meta = f"Priorytet: {card.priority}    Termin: {card.due_date or 'brak'}    Progress: {card.checklist_progress}%"
        ttk.Label(frame, text=meta).grid(row=1, column=0, sticky="w", pady=(0, 10))

        notebook = ttk.Notebook(frame)
        notebook.grid(row=2, column=0, sticky="nsew")
        frame.rowconfigure(2, weight=1)

        def tab_text(title: str, content: str) -> None:
            tab = ttk.Frame(notebook, padding=10)
            text = tk.Text(tab, wrap="word", height=10)
            text.pack(fill="both", expand=True)
            text.insert("1.0", content)
            text.configure(state="disabled")
            notebook.add(tab, text=title)

        labels = ", ".join(label.name for label in card.labels) or "brak"
        members = ", ".join(card.members) or "brak"
        details = (
            f"Opis:\n{card.description or 'brak'}\n\n"
            f"Etykiety: {labels}\n"
            f"Członkowie: {members}\n"
            f"Utworzono: {card.created_at}\n"
            f"Aktualizacja: {card.updated_at}\n"
            f"Archiwum: {'tak' if card.archived else 'nie'}\n"
        )
        tab_text("Opis", details)
        checklist = "\n".join(("☑ " if item.done else "☐ ") + item.text for item in card.checklist) or "Brak checklisty"
        tab_text("Checklist", checklist)
        comments = "\n\n".join(f"{comment.created_at} — {comment.author}\n{comment.text}" for comment in card.comments) or "Brak komentarzy"
        tab_text("Komentarze", comments)
        attachments = "\n".join(f"📎 {attachment.name or attachment.path}\n{attachment.path}" for attachment in card.attachments) or "Brak załączników"
        tab_text("Załączniki", attachments)
        dependencies = "\n".join(card.dependencies) or "Brak zależności"
        tab_text("Zależności", dependencies)

        ttk.Button(frame, text="Zamknij", command=self.destroy).grid(row=3, column=0, sticky="e", pady=(10, 0))


class SettingsDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, settings: dict, themes: list[str]) -> None:
        super().__init__(master)
        self.title("Ustawienia")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result: dict | None = None
        self.settings = dict(settings)

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Motyw").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        ttk.Combobox(frame, textvariable=self.theme_var, values=themes, state="readonly", width=24).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(frame, text="Backup co ile minut").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.backup_var = tk.StringVar(value=str(self.settings.get("backup_minutes", 5)))
        ttk.Entry(frame, textvariable=self.backup_var, width=24).grid(row=3, column=0, sticky="ew", pady=(0, 10))

        self.notifications_var = tk.BooleanVar(value=bool(self.settings.get("notifications", True)))
        ttk.Checkbutton(frame, text="Powiadomienia lokalne", variable=self.notifications_var).grid(row=4, column=0, sticky="w", pady=(0, 12))

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, sticky="e")
        ttk.Button(buttons, text="Anuluj", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Zapisz", command=self.save).pack(side="right")

    def save(self) -> None:
        try:
            backup_minutes = max(1, int(self.backup_var.get()))
        except ValueError:
            messagebox.showwarning("Ustawienia", "Backup musi być liczbą minut.", parent=self)
            return
        self.result = {
            **self.settings,
            "theme": self.theme_var.get(),
            "backup_minutes": backup_minutes,
            "notifications": self.notifications_var.get(),
        }
        self.destroy()


class LabelManagerDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, labels: list[Label]) -> None:
        super().__init__(master)
        self.title("Etykiety tablicy")
        self.geometry("420x360")
        self.transient(master)
        self.grab_set()
        self.result: list[Label] | None = None
        self.labels = [Label(id=label.id, name=label.name, color=label.color) for label in labels]

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(frame, height=10)
        self.listbox.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=(0, 8))
        frame.rowconfigure(0, weight=1)

        ttk.Label(frame, text="Nazwa").grid(row=1, column=0, sticky="w")
        ttk.Label(frame, text="Kolor HEX").grid(row=1, column=1, sticky="w")
        self.name_var = tk.StringVar()
        self.color_var = tk.StringVar(value="#3b82f6")
        ttk.Entry(frame, textvariable=self.name_var).grid(row=2, column=0, sticky="ew", padx=(0, 6))
        ttk.Entry(frame, textvariable=self.color_var, width=12).grid(row=2, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(frame, text="Dodaj", command=self.add_label).grid(row=2, column=2)
        ttk.Button(frame, text="Usuń zaznaczoną", command=self.delete_selected).grid(row=3, column=0, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Anuluj", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Zapisz", command=self.save).pack(side="right")
        self.refresh()

    def refresh(self) -> None:
        self.listbox.delete(0, "end")
        for label in self.labels:
            self.listbox.insert("end", f"{label.name}  {label.color}")

    def add_label(self) -> None:
        name = self.name_var.get().strip()
        color = self.color_var.get().strip() or "#3b82f6"
        if not name:
            messagebox.showwarning("Etykiety", "Podaj nazwę etykiety.", parent=self)
            return
        self.labels.append(Label(name=name, color=color))
        self.name_var.set("")
        self.refresh()

    def delete_selected(self) -> None:
        selection = self.listbox.curselection()
        if selection:
            del self.labels[selection[0]]
            self.refresh()

    def save(self) -> None:
        self.result = self.labels
        self.destroy()


def show_about(master: tk.Misc) -> None:
    messagebox.showinfo(
        "O aplikacji",
        "Better Trello 2.7\n\nLokalna aplikacja desktopowa Tkinter + opcjonalny FastAPI backend + AI Chat podpięty pod OpenRouter/Ollama/offline fallback + lokalny system pluginów.",
        parent=master,
    )
