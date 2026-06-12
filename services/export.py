from __future__ import annotations

import csv
import json
import zipfile
from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from models.board import Board
from models.card import Card
from models.column import Column
from models.label import Label


class ExportService:
    @staticmethod
    def export_json(board: Board, file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(board.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def export_csv(board: Board, file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Kolumna", "Zadanie", "Opis", "Priorytet", "Termin", "Etykiety", "Użytkownicy", "Archiwum"])
            for column in board.columns:
                for card in column.cards:
                    writer.writerow([
                        column.name,
                        card.title,
                        card.description,
                        card.priority,
                        card.due_date or "",
                        ", ".join(label.name for label in card.labels),
                        ", ".join(card.members),
                        "tak" if card.archived else "nie",
                    ])

    @staticmethod
    def import_csv_to_board(board: Board, file_path: str | Path) -> int:
        """Importuje karty z CSV do istniejącej tablicy.

        Oczekiwane nagłówki są zgodne z eksportem CSV, ale importer toleruje też
        prostsze nazwy: column/title/description/priority/due_date/labels/members.
        Zwraca liczbę dodanych kart.
        """
        path = Path(file_path)
        added = 0
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                column_name = row.get("Kolumna") or row.get("column") or row.get("Column") or "Import"
                title = row.get("Zadanie") or row.get("title") or row.get("Title") or row.get("task") or "Bez tytułu"
                description = row.get("Opis") or row.get("description") or row.get("Description") or ""
                priority = (row.get("Priorytet") or row.get("priority") or "medium").lower()
                due_date = row.get("Termin") or row.get("due_date") or row.get("Due Date") or None
                labels_raw = row.get("Etykiety") or row.get("labels") or ""
                members_raw = row.get("Użytkownicy") or row.get("members") or ""

                column = next((item for item in board.columns if item.name == column_name), None)
                if column is None:
                    column = Column(name=column_name)
                    board.columns.append(column)

                labels = [Label(name=name.strip()) for name in labels_raw.split(",") if name.strip()]
                members = [name.strip() for name in members_raw.split(",") if name.strip()]
                column.cards.append(
                    Card(
                        title=title,
                        description=description,
                        priority=priority if priority in {"low", "medium", "high"} else "medium",
                        due_date=due_date or None,
                        labels=labels,
                        members=members,
                    )
                )
                added += 1
        board.add_activity("csv_imported", f"Zaimportowano {added} kart z {path.name}")
        return added

    @staticmethod
    def export_html(board: Board, file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        columns = []
        for column in board.columns:
            cards = "".join(
                f"<li><strong>{escape(card.title)}</strong><br><small>{escape(card.description)}</small></li>"
                for card in column.cards if not card.archived
            )
            columns.append(f"<section><h2>{escape(column.name)}</h2><ul>{cards}</ul></section>")
        html = f"""<!doctype html>
<html lang="pl"><meta charset="utf-8"><title>{escape(board.name)}</title>
<style>body{{font-family:Arial,sans-serif;background:#f3f4f6}}main{{display:flex;gap:16px}}section{{background:white;border-radius:10px;padding:16px;min-width:240px}}li{{margin:10px 0;padding:10px;background:#f9fafb;border-radius:8px}}</style>
<h1>{escape(board.name)}</h1><main>{''.join(columns)}</main></html>"""
        path.write_text(html, encoding="utf-8")

    @staticmethod
    def export_xlsx(board: Board, file_path: str | Path) -> None:
        """Tworzy prosty, prawdziwy plik XLSX bez zewnętrznych bibliotek."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [["Kolumna", "Zadanie", "Opis", "Priorytet", "Termin", "Etykiety", "Użytkownicy", "Archiwum"]]
        for column in board.columns:
            for card in column.cards:
                rows.append([
                    column.name,
                    card.title,
                    card.description,
                    card.priority,
                    card.due_date or "",
                    ", ".join(label.name for label in card.labels),
                    ", ".join(card.members),
                    "tak" if card.archived else "nie",
                ])

        sheet_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for col_index, value in enumerate(row, start=1):
                cell_ref = f"{ExportService._xlsx_col(col_index)}{row_index}"
                cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{xml_escape(str(value))}</t></is></c>')
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

        worksheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>'''
        workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Kanban" sheetId="1" r:id="rId1"/></sheets></workbook>'''
        rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
        workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'''
        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'''
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", rels)
            archive.writestr("xl/workbook.xml", workbook)
            archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            archive.writestr("xl/worksheets/sheet1.xml", worksheet)

    @staticmethod
    def _xlsx_col(index: int) -> str:
        result = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @staticmethod
    def export_pdf_text_fallback(board: Board, file_path: str | Path) -> None:
        # Bez zewnętrznych bibliotek generujemy czytelny plik tekstowy z rozszerzeniem .pdf.
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"Kanban Board: {board.name}", ""]
        for column in board.columns:
            lines.append(f"## {column.name}")
            for card in column.cards:
                if not card.archived:
                    lines.append(f"- {card.title} [{card.priority}] {card.due_date or ''}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
