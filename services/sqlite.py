from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from models.activity import ActivityLog
from models.attachment import Attachment
from models.board import Board
from models.card import Card
from models.checklist import ChecklistItem
from models.column import Column
from models.comment import Comment
from models.label import Label
from models.workspace import Workspace


SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, name TEXT NOT NULL, active_board_id TEXT);
CREATE TABLE IF NOT EXISTS boards (id TEXT PRIMARY KEY, workspace_id TEXT, name TEXT NOT NULL, favorite INTEGER DEFAULT 0, archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS columns (id TEXT PRIMARY KEY, board_id TEXT, name TEXT NOT NULL, position INTEGER DEFAULT 0, emoji TEXT, archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, column_id TEXT, title TEXT NOT NULL, description TEXT, priority TEXT, due_date TEXT, members TEXT, cover_color TEXT, archived INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT, dependencies TEXT, template TEXT);
CREATE TABLE IF NOT EXISTS comments (id TEXT PRIMARY KEY, card_id TEXT, text TEXT, author TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS attachments (id TEXT PRIMARY KEY, card_id TEXT, path TEXT, name TEXT);
CREATE TABLE IF NOT EXISTS labels (id TEXT PRIMARY KEY, board_id TEXT, name TEXT, color TEXT);
CREATE TABLE IF NOT EXISTS card_labels (card_id TEXT, label_id TEXT, PRIMARY KEY(card_id, label_id));
CREATE TABLE IF NOT EXISTS activities (id TEXT PRIMARY KEY, board_id TEXT, action TEXT, details TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS checklists (id TEXT PRIMARY KEY, card_id TEXT, text TEXT, done INTEGER DEFAULT 0);
"""


class SQLiteService:
    """Lokalny storage SQLite.

    JSON nadal zostaje formatem importu/eksportu, ale ta klasa potrafi zapisać i
    odczytać workspace w znormalizowanych tabelach SQLite bez internetu.
    """

    def __init__(self, db_path: str | Path = "database/kanban.sqlite3") -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate_cards_table(conn)

    def _migrate_cards_table(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(cards)")}
        migrations = {
            "members": "ALTER TABLE cards ADD COLUMN members TEXT",
            "dependencies": "ALTER TABLE cards ADD COLUMN dependencies TEXT",
            "template": "ALTER TABLE cards ADD COLUMN template TEXT",
        }
        for column, statement in migrations.items():
            if column not in columns:
                conn.execute(statement)

    def save_workspace(self, workspace: Workspace) -> None:
        self.initialize()
        with self.connect() as conn:
            self._clear(conn)
            conn.execute(
                "INSERT INTO workspaces (id, name, active_board_id) VALUES (?, ?, ?)",
                (workspace.id, workspace.name, workspace.active_board_id),
            )
            for board in workspace.boards:
                conn.execute(
                    "INSERT INTO boards (id, workspace_id, name, favorite, archived) VALUES (?, ?, ?, ?, ?)",
                    (board.id, workspace.id, board.name, int(board.favorite), int(board.archived)),
                )
                for label in board.labels:
                    conn.execute(
                        "INSERT OR REPLACE INTO labels (id, board_id, name, color) VALUES (?, ?, ?, ?)",
                        (label.id, board.id, label.name, label.color),
                    )
                for activity in board.activities:
                    conn.execute(
                        "INSERT INTO activities (id, board_id, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
                        (activity.id, board.id, activity.action, activity.details, activity.created_at),
                    )
                for position, column in enumerate(board.columns):
                    conn.execute(
                        "INSERT INTO columns (id, board_id, name, position, emoji, archived) VALUES (?, ?, ?, ?, ?, ?)",
                        (column.id, board.id, column.name, position, column.emoji, int(column.archived)),
                    )
                    for card in column.cards:
                        conn.execute(
                            """
                            INSERT INTO cards
                            (id, column_id, title, description, priority, due_date, members, cover_color, archived, created_at, updated_at, dependencies, template)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                card.id,
                                column.id,
                                card.title,
                                card.description,
                                card.priority,
                                card.due_date,
                                json.dumps(card.members, ensure_ascii=False),
                                card.cover_color,
                                int(card.archived),
                                card.created_at,
                                card.updated_at,
                                json.dumps(card.dependencies, ensure_ascii=False),
                                card.template,
                            ),
                        )
                        for label in card.labels:
                            conn.execute(
                                "INSERT OR REPLACE INTO labels (id, board_id, name, color) VALUES (?, ?, ?, ?)",
                                (label.id, board.id, label.name, label.color),
                            )
                            conn.execute(
                                "INSERT OR IGNORE INTO card_labels (card_id, label_id) VALUES (?, ?)",
                                (card.id, label.id),
                            )
                        for comment in card.comments:
                            conn.execute(
                                "INSERT INTO comments (id, card_id, text, author, created_at) VALUES (?, ?, ?, ?, ?)",
                                (comment.id, card.id, comment.text, comment.author, comment.created_at),
                            )
                        for attachment in card.attachments:
                            conn.execute(
                                "INSERT INTO attachments (id, card_id, path, name) VALUES (?, ?, ?, ?)",
                                (attachment.id, card.id, attachment.path, attachment.name),
                            )
                        for item in card.checklist:
                            conn.execute(
                                "INSERT INTO checklists (id, card_id, text, done) VALUES (?, ?, ?, ?)",
                                (item.id, card.id, item.text, int(item.done)),
                            )

    def load_workspace(self) -> Workspace:
        self.initialize()
        with self.connect() as conn:
            workspace_row = conn.execute("SELECT * FROM workspaces LIMIT 1").fetchone()
            if workspace_row is None:
                workspace = Workspace.default()
                self.save_workspace(workspace)
                return workspace

            workspace = Workspace(id=workspace_row["id"], name=workspace_row["name"], active_board_id=workspace_row["active_board_id"], boards=[])
            for board_row in conn.execute("SELECT * FROM boards WHERE workspace_id = ? ORDER BY name", (workspace.id,)):
                board = Board(
                    id=board_row["id"],
                    name=board_row["name"],
                    favorite=bool(board_row["favorite"]),
                    archived=bool(board_row["archived"]),
                    columns=[],
                    labels=[],
                    activities=[],
                )
                labels_by_id: dict[str, Label] = {}
                for label_row in conn.execute("SELECT * FROM labels WHERE board_id = ?", (board.id,)):
                    label = Label(id=label_row["id"], name=label_row["name"], color=label_row["color"])
                    labels_by_id[label.id] = label
                    board.labels.append(label)
                for activity_row in conn.execute("SELECT * FROM activities WHERE board_id = ? ORDER BY created_at DESC", (board.id,)):
                    board.activities.append(ActivityLog(id=activity_row["id"], action=activity_row["action"], details=activity_row["details"], created_at=activity_row["created_at"]))
                for column_row in conn.execute("SELECT * FROM columns WHERE board_id = ? ORDER BY position", (board.id,)):
                    column = Column(id=column_row["id"], name=column_row["name"], emoji=column_row["emoji"] or "", archived=bool(column_row["archived"]), cards=[])
                    for card_row in conn.execute("SELECT * FROM cards WHERE column_id = ?", (column.id,)):
                        card = Card(
                            id=card_row["id"],
                            title=card_row["title"],
                            description=card_row["description"] or "",
                            priority=card_row["priority"] or "medium",
                            due_date=card_row["due_date"],
                            members=json.loads(card_row["members"] or "[]"),
                            cover_color=card_row["cover_color"] or "",
                            archived=bool(card_row["archived"]),
                            created_at=card_row["created_at"],
                            updated_at=card_row["updated_at"],
                            dependencies=json.loads(card_row["dependencies"] or "[]"),
                            template=card_row["template"] or "",
                        )
                        for label_link in conn.execute("SELECT label_id FROM card_labels WHERE card_id = ?", (card.id,)):
                            if label_link["label_id"] in labels_by_id:
                                card.labels.append(labels_by_id[label_link["label_id"]])
                        for comment_row in conn.execute("SELECT * FROM comments WHERE card_id = ? ORDER BY created_at", (card.id,)):
                            card.comments.append(Comment(id=comment_row["id"], text=comment_row["text"], author=comment_row["author"], created_at=comment_row["created_at"]))
                        for attachment_row in conn.execute("SELECT * FROM attachments WHERE card_id = ?", (card.id,)):
                            card.attachments.append(Attachment(id=attachment_row["id"], path=attachment_row["path"], name=attachment_row["name"]))
                        for checklist_row in conn.execute("SELECT * FROM checklists WHERE card_id = ?", (card.id,)):
                            card.checklist.append(ChecklistItem(id=checklist_row["id"], text=checklist_row["text"], done=bool(checklist_row["done"])))
                        column.cards.append(card)
                    board.columns.append(column)
                workspace.boards.append(board)
            if not workspace.active_board_id and workspace.boards:
                workspace.active_board_id = workspace.boards[0].id
            return workspace

    def _clear(self, conn: sqlite3.Connection) -> None:
        for table in [
            "card_labels",
            "checklists",
            "comments",
            "attachments",
            "cards",
            "labels",
            "activities",
            "columns",
            "boards",
            "workspaces",
        ]:
            conn.execute(f"DELETE FROM {table}")
