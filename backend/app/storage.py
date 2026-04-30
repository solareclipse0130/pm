from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
DEFAULT_DATABASE_PATH = PROJECT_DIR / "data" / "app.db"
MVP_USERNAME = "user"

MAX_COLUMNS = 50
MAX_CARDS = 1000
MAX_ID_LENGTH = 100
MAX_TITLE_LENGTH = 200
MAX_DETAILS_LENGTH = 5000


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def get_database_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH))


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    with connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS boards (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL UNIQUE,
              data TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
        )


def create_default_board(timestamp: str | None = None) -> dict[str, Any]:
    now = timestamp or utc_now()
    cards = {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    }
    return {
        "version": 1,
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
            {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
            {
                "id": "col-progress",
                "title": "In Progress",
                "cardIds": ["card-4", "card-5"],
            },
            {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
            {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
        ],
        "cards": {
            card_id: {**card, "createdAt": now, "updatedAt": now}
            for card_id, card in cards.items()
        },
    }


def validate_board(board: Any) -> None:
    if not isinstance(board, dict):
        raise ValueError("Board must be an object.")
    if board.get("version") != 1:
        raise ValueError("Board version must be 1.")

    columns = board.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ValueError("Board must include at least one column.")
    if len(columns) > MAX_COLUMNS:
        raise ValueError(f"Board may include at most {MAX_COLUMNS} columns.")

    cards = board.get("cards")
    if not isinstance(cards, dict):
        raise ValueError("Board cards must be an object.")
    if len(cards) > MAX_CARDS:
        raise ValueError(f"Board may include at most {MAX_CARDS} cards.")

    column_ids: set[str] = set()
    referenced_card_ids: list[str] = []

    for column in columns:
        if not isinstance(column, dict):
            raise ValueError("Each column must be an object.")
        column_id = column.get("id")
        if not isinstance(column_id, str) or not column_id:
            raise ValueError("Each column must have an id.")
        if len(column_id) > MAX_ID_LENGTH:
            raise ValueError(
                f"Column id must be {MAX_ID_LENGTH} characters or fewer."
            )
        if column_id in column_ids:
            raise ValueError("Column ids must be unique.")
        column_ids.add(column_id)
        title = column.get("title")
        if not isinstance(title, str):
            raise ValueError("Each column must have a title.")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(
                f"Column title must be {MAX_TITLE_LENGTH} characters or fewer."
            )
        card_ids = column.get("cardIds")
        if not isinstance(card_ids, list) or not all(
            isinstance(card_id, str) for card_id in card_ids
        ):
            raise ValueError("Each column must have cardIds as strings.")
        referenced_card_ids.extend(card_ids)

    if len(referenced_card_ids) != len(set(referenced_card_ids)):
        raise ValueError("A card can appear in only one column.")

    for card_id, card in cards.items():
        if not isinstance(card_id, str) or not isinstance(card, dict):
            raise ValueError("Each card must be keyed by id.")
        if len(card_id) > MAX_ID_LENGTH:
            raise ValueError(
                f"Card id must be {MAX_ID_LENGTH} characters or fewer."
            )
        if card.get("id") != card_id:
            raise ValueError("Card keys must match card ids.")
        title = card.get("title")
        if not isinstance(title, str):
            raise ValueError("Each card must have a title.")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(
                f"Card title must be {MAX_TITLE_LENGTH} characters or fewer."
            )
        details = card.get("details")
        if not isinstance(details, str):
            raise ValueError("Each card must have details.")
        if len(details) > MAX_DETAILS_LENGTH:
            raise ValueError(
                f"Card details must be {MAX_DETAILS_LENGTH} characters or fewer."
            )
        if not isinstance(card.get("createdAt"), str):
            raise ValueError("Each card must have createdAt.")
        if not isinstance(card.get("updatedAt"), str):
            raise ValueError("Each card must have updatedAt.")

    referenced = set(referenced_card_ids)
    card_keys = set(cards.keys())
    missing = referenced - card_keys
    if missing:
        raise ValueError("Every cardIds entry must refer to an existing card.")
    if card_keys - referenced:
        raise ValueError("Every card must be assigned to a column.")


def get_or_create_user(connection: sqlite3.Connection, username: str) -> int:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO users (username, created_at, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO NOTHING
        """,
        (username, now, now),
    )
    row = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return int(row["id"])


def get_or_create_board(
    database_path: Path,
    username: str = MVP_USERNAME,
) -> dict[str, Any]:
    initialize_database(database_path)
    with connect(database_path) as connection:
        user_id = get_or_create_user(connection, username)
        row = connection.execute(
            "SELECT data FROM boards WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            return json.loads(row["data"])

        now = utc_now()
        board = create_default_board(now)
        validate_board(board)
        connection.execute(
            """
            INSERT INTO boards (user_id, data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, json.dumps(board, separators=(",", ":")), now, now),
        )
        row = connection.execute(
            "SELECT data FROM boards WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return json.loads(row["data"])


def save_board(
    database_path: Path,
    board: dict[str, Any],
    username: str = MVP_USERNAME,
) -> dict[str, Any]:
    validate_board(board)
    initialize_database(database_path)
    with connect(database_path) as connection:
        user_id = get_or_create_user(connection, username)
        now = utc_now()
        connection.execute(
            """
            INSERT INTO boards (user_id, data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              data = excluded.data,
              updated_at = excluded.updated_at
            """,
            (user_id, json.dumps(board, separators=(",", ":")), now, now),
        )
        return board
