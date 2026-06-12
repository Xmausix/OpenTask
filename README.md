# Local Trello Pro 2.0

Lokalna aplikacja desktopowa Tkinter do zarządzania zadaniami metodą Kanban/Trello. Działa bez internetu, bez kont użytkowników i zapisuje dane lokalnie do JSON. SQLite jest przygotowane jako fundament pod kolejną iterację.

## Uruchomienie

```bash
cd kanban-board
python3 main.py
```

## Co jest zaimplementowane w wersji 2.0

### Workspace i wiele tablic

- Model `Workspace`
- Lista tablic w bocznym panelu
- Tworzenie tablic
- Usuwanie tablic
- Kopiowanie tablic
- Archiwizacja tablic
- Ulubione tablice
- Zapis/odczyt całego workspace do JSON
- Wsteczna kompatybilność: można otworzyć stary JSON pojedynczej tablicy

### Bogatsze karty

Model `Card` zawiera teraz:

- `title`
- `description`
- `priority`
- `labels`
- `due_date`
- `members`
- `attachments`
- `checklist`
- `comments`
- `cover_color`
- `archived`
- `created_at`
- `updated_at`
- `dependencies`
- `template`

Dwuklik na kartę otwiera edycję. Prawy klik pokazuje menu kontekstowe.

### Checklisty

- Pozycje checklisty jako `ChecklistItem`
- Procent postępu na karcie
- Obsługa wpisów `[x] Gotowe` i `[ ] Do zrobienia`

### Komentarze

- Model `Comment`
- Dodawanie komentarzy w edycji karty
- Licznik komentarzy na karcie

### Załączniki

- Model `Attachment`
- Dodawanie plików przez selektor plików
- Obsługiwane filtry: PDF, DOCX, JPG, PNG, ZIP
- Licznik załączników na karcie

### Etykiety

- Model `Label`
- Presety: Backend, API, Bug, Critical, Frontend, Docs
- Filtrowanie po etykietach

### Terminy

- Pole `due_date`
- Widok terminu na karcie
- Lokalne przypomnienia w pasku tytułu: termin dziś, za 1 dzień, po terminie

### Archiwizacja

- Archiwizacja kart
- Filtr `Archiwum`
- Archiwizacja tablic

### Wyszukiwarka i filtry

Globalna wyszukiwarka przeszukuje:

- tytuły
- opisy
- komentarze
- etykiety

Filtry:

- priorytet
- etykieta
- termin
- archiwum

Sortowanie:

- termin
- priorytet
- data utworzenia
- alfabetycznie

### Przeciąganie

- Drag & drop kart między kolumnami
- Przesuwanie kolumn w lewo/prawo z menu `⋯`

### Widoki

- Kanban
- Table
- Dashboard
- Calendar — uproszczony lokalny widok kart z terminami
- Timeline — uproszczony widok tekstowy/Gantt

### Eksport i backup

- Eksport JSON
- Eksport CSV
- Eksport HTML
- Eksport PDF fallback jako czytelny plik tekstowy `.pdf` bez zewnętrznych bibliotek
- Automatyczny backup co 5 minut do `/backups`
- Ręczny backup z menu `File`

### SQLite

Plik `services/sqlite.py` zawiera schemat tabel:

- `workspaces`
- `boards`
- `columns`
- `cards`
- `comments`
- `attachments`
- `labels`
- `card_labels`
- `activities`
- `checklists`

JSON pozostaje aktywnym formatem importu/eksportu.

## Struktura

```text
kanban-board/
├── main.py
├── models/
│   ├── workspace.py
│   ├── board.py
│   ├── column.py
│   ├── card.py
│   ├── label.py
│   ├── comment.py
│   ├── attachment.py
│   ├── checklist.py
│   ├── activity.py
│   └── sprint.py
├── services/
│   ├── storage.py
│   ├── sqlite.py
│   ├── dragdrop.py
│   ├── backup.py
│   ├── export.py
│   ├── notifications.py
│   └── search.py
├── ui/
│   ├── board_view.py
│   ├── calendar_view.py
│   ├── timeline_view.py
│   ├── dashboard_view.py
│   ├── table_view.py
│   ├── dialogs.py
│   └── settings.py
├── plugins/
├── backups/
├── exports/
├── database/
└── assets/
```

## Skróty

- `Ctrl+N` — nowa tablica
- `Ctrl+S` — zapisz workspace
- `Ctrl+O` — otwórz workspace
- `Ctrl+F` — wyszukiwarka
- `Ctrl+Z` / `Ctrl+Y` — przygotowane komunikaty pod przyszły pełny undo/redo
