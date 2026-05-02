from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
DEFAULT_DATABASE_PATH = PROJECT_DIR / "data" / "app.db"

MVP_USERNAME = "user"
MVP_PASSWORD = "password"
MVP_DISPLAY_NAME = "MVP User"

SCHEMA_VERSION = 1
SESSION_TTL_SECONDS = 30 * 24 * 3600
SESSION_TOKEN_BYTES = 32

MAX_USERNAME_LENGTH = 64
MIN_USERNAME_LENGTH = 3
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256

MAX_DISPLAY_NAME_LENGTH = 120
MAX_BOARD_TITLE_LENGTH = 120
MAX_BOARD_DESCRIPTION_LENGTH = 500
MAX_BOARDS_PER_USER = 50

MAX_COLUMNS = 50
MAX_CARDS = 1000
MAX_ID_LENGTH = 100
MAX_TITLE_LENGTH = 200
MAX_DETAILS_LENGTH = 5000
MAX_LABEL_LENGTH = 40
MAX_LABELS_PER_CARD = 10

ALLOWED_PRIORITIES = {"low", "medium", "high", "urgent"}
DUE_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_SALT_BYTES = 16


class StorageError(ValueError):
    """Raised when a storage operation is rejected for input reasons."""


class AuthError(StorageError):
    """Raised on authentication failures (wrong password, expired session, ...)."""


class NotFoundError(StorageError):
    """Raised when an entity does not exist or is not visible to the caller."""


class ConflictError(StorageError):
    """Raised when an operation conflicts with concurrent state."""


def utc_now() -> str:
    """Return an ISO 8601 UTC timestamp with microsecond precision.

    The microsecond suffix keeps `updated_at` strictly monotonic across
    rapid successive writes, which the optimistic-concurrency check relies
    on to detect mid-flight changes.
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


def get_database_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH))


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE COLLATE NOCASE,
          password_hash TEXT NOT NULL,
          display_name TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
          token TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user
          ON sessions (user_id);

        CREATE TABLE IF NOT EXISTS boards (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL,
          title TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '',
          position INTEGER NOT NULL DEFAULT 0,
          data TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_boards_owner
          ON boards (owner_id);
        """
    )


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _migrate_legacy_v0(connection: sqlite3.Connection) -> None:
    """Migrate any pre-multi-user data (single board per user, no password)."""
    if not _table_exists(connection, "users"):
        return  # fresh database, nothing to migrate

    user_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    if "password_hash" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''"
        )
        connection.execute(
            "ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''"
        )

    board_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(boards)").fetchall()
    }
    if "user_id" in board_columns and "owner_id" not in board_columns:
        # The legacy schema has a unique user_id column. SQLite cannot drop a
        # UNIQUE constraint in place, so rebuild the table.
        connection.executescript(
            """
            ALTER TABLE boards RENAME TO boards_legacy;
            CREATE TABLE boards (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              owner_id INTEGER NOT NULL,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              position INTEGER NOT NULL DEFAULT 0,
              data TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE
            );
            INSERT INTO boards (owner_id, title, description, position, data, created_at, updated_at)
              SELECT user_id, 'My Board', '', 0, data, created_at, updated_at FROM boards_legacy;
            DROP TABLE boards_legacy;
            CREATE INDEX IF NOT EXISTS idx_boards_owner ON boards (owner_id);
            """
        )

    # Make sure any pre-existing user without a password gets the MVP default.
    rows = connection.execute(
        "SELECT id, username FROM users WHERE password_hash = '' OR password_hash IS NULL"
    ).fetchall()
    for row in rows:
        new_hash = hash_password(MVP_PASSWORD)
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, row["id"]),
        )

    # Migrate existing board JSON to ensure card extensions are present.
    rows = connection.execute("SELECT id, data FROM boards").fetchall()
    for row in rows:
        try:
            board = json.loads(row["data"])
        except json.JSONDecodeError:
            continue
        normalized = normalize_board(board)
        connection.execute(
            "UPDATE boards SET data = ? WHERE id = ?",
            (json.dumps(normalized, separators=(",", ":")), row["id"]),
        )


def _seed_mvp_user(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT id FROM users WHERE username = ? COLLATE NOCASE",
        (MVP_USERNAME,),
    ).fetchone()
    if row:
        return
    now = utc_now()
    password_hash = hash_password(MVP_PASSWORD)
    connection.execute(
        """
        INSERT INTO users (username, password_hash, display_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (MVP_USERNAME, password_hash, MVP_DISPLAY_NAME, now, now),
    )
    user_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
    _seed_default_board(connection, user_id, now)


def _seed_default_board(
    connection: sqlite3.Connection, user_id: int, now: str
) -> int:
    board = create_default_board(now)
    cursor = connection.execute(
        """
        INSERT INTO boards (owner_id, title, description, position, data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            "My Board",
            "Default board for getting started.",
            0,
            json.dumps(board, separators=(",", ":")),
            now,
            now,
        ),
    )
    return int(cursor.lastrowid)


def initialize_database(database_path: Path) -> None:
    with connect(database_path) as connection:
        version_row = connection.execute("PRAGMA user_version").fetchone()
        current_version = int(version_row[0]) if version_row else 0
        # Migrate legacy single-user/single-board layout BEFORE creating the
        # new schema, so that `CREATE INDEX ... owner_id` does not collide
        # with the legacy `user_id` column.
        if current_version < SCHEMA_VERSION:
            _migrate_legacy_v0(connection)
        _create_schema(connection)
        if current_version < SCHEMA_VERSION:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        _seed_mvp_user(connection)


# --- Password hashing -------------------------------------------------------


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise StorageError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise StorageError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        )
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    derived_b64 = base64.b64encode(derived).decode("ascii")
    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt_b64}${derived_b64}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    parts = password_hash.split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        n = int(parts[1])
        r = int(parts[2])
        p = int(parts[3])
        salt = base64.b64decode(parts[4])
        expected = base64.b64decode(parts[5])
    except (ValueError, base64.binascii.Error):
        return False
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=len(expected),
    )
    return hmac.compare_digest(derived, expected)


# --- User management --------------------------------------------------------


def _validate_username(username: Any) -> str:
    if not isinstance(username, str):
        raise StorageError("Username must be a string.")
    cleaned = username.strip()
    if len(cleaned) < MIN_USERNAME_LENGTH:
        raise StorageError(
            f"Username must be at least {MIN_USERNAME_LENGTH} characters."
        )
    if len(cleaned) > MAX_USERNAME_LENGTH:
        raise StorageError(
            f"Username must be at most {MAX_USERNAME_LENGTH} characters."
        )
    if not USERNAME_PATTERN.match(cleaned):
        raise StorageError(
            "Username may only contain letters, digits, dot, underscore, or hyphen."
        )
    return cleaned


def _validate_display_name(display_name: Any) -> str:
    if display_name is None:
        return ""
    if not isinstance(display_name, str):
        raise StorageError("Display name must be a string.")
    cleaned = display_name.strip()
    if len(cleaned) > MAX_DISPLAY_NAME_LENGTH:
        raise StorageError(
            f"Display name must be at most {MAX_DISPLAY_NAME_LENGTH} characters."
        )
    return cleaned


def _user_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "displayName": row["display_name"] or "",
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def create_user(
    database_path: Path,
    username: str,
    password: str,
    display_name: str | None = None,
    seed_default_board: bool = True,
) -> dict[str, Any]:
    initialize_database(database_path)
    cleaned_username = _validate_username(username)
    cleaned_display = _validate_display_name(display_name)
    password_hash = hash_password(password)
    now = utc_now()
    with connect(database_path) as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ? COLLATE NOCASE",
            (cleaned_username,),
        ).fetchone()
        if existing:
            raise ConflictError("Username is already taken.")
        cursor = connection.execute(
            """
            INSERT INTO users (username, password_hash, display_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cleaned_username, password_hash, cleaned_display, now, now),
        )
        user_id = int(cursor.lastrowid)
        if seed_default_board:
            _seed_default_board(connection, user_id, now)
        row = connection.execute(
            "SELECT id, username, display_name, created_at, updated_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return _user_to_dict(row)


def authenticate(
    database_path: Path, username: str, password: str
) -> dict[str, Any]:
    initialize_database(database_path)
    if not isinstance(username, str) or not isinstance(password, str):
        raise AuthError("Invalid username or password.")
    cleaned_username = username.strip()
    if not cleaned_username:
        raise AuthError("Invalid username or password.")
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, username, password_hash, display_name, created_at, updated_at "
            "FROM users WHERE username = ? COLLATE NOCASE",
            (cleaned_username,),
        ).fetchone()
    if row is None:
        raise AuthError("Invalid username or password.")
    if not verify_password(password, row["password_hash"]):
        raise AuthError("Invalid username or password.")
    return _user_to_dict(row)


def get_user(database_path: Path, user_id: int) -> dict[str, Any] | None:
    initialize_database(database_path)
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, username, display_name, created_at, updated_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return _user_to_dict(row) if row else None


def update_user_profile(
    database_path: Path,
    user_id: int,
    display_name: str | None = None,
) -> dict[str, Any]:
    initialize_database(database_path)
    cleaned_display = _validate_display_name(display_name)
    now = utc_now()
    with connect(database_path) as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if existing is None:
            raise NotFoundError("User does not exist.")
        connection.execute(
            "UPDATE users SET display_name = ?, updated_at = ? WHERE id = ?",
            (cleaned_display, now, user_id),
        )
        row = connection.execute(
            "SELECT id, username, display_name, created_at, updated_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return _user_to_dict(row)


def change_password(
    database_path: Path,
    user_id: int,
    current_password: str,
    new_password: str,
) -> None:
    initialize_database(database_path)
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError("User does not exist.")
        if not verify_password(current_password, row["password_hash"]):
            raise AuthError("Current password is incorrect.")
        new_hash = hash_password(new_password)
        connection.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (new_hash, utc_now(), user_id),
        )
        # Invalidate all existing sessions on password change.
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


# --- Sessions ---------------------------------------------------------------


def _prune_expired_sessions(connection: sqlite3.Connection) -> None:
    connection.execute(
        "DELETE FROM sessions WHERE expires_at <= ?", (utc_now(),)
    )


def create_session(
    database_path: Path, user_id: int, ttl_seconds: int = SESSION_TTL_SECONDS
) -> dict[str, Any]:
    initialize_database(database_path)
    token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
    # Use the same microsecond precision as utc_now() so created_at, expires_at
    # and the comparison value used by _prune_expired_sessions sort
    # lexicographically together.
    now_dt = datetime.now(timezone.utc)
    created_at = now_dt.isoformat().replace("+00:00", "Z")
    expires_at = (now_dt + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z")
    with connect(database_path) as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if existing is None:
            raise NotFoundError("User does not exist.")
        _prune_expired_sessions(connection)
        connection.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, created_at, expires_at),
        )
    return {"token": token, "expiresAt": expires_at, "createdAt": created_at}


def resolve_session(database_path: Path, token: str) -> dict[str, Any]:
    initialize_database(database_path)
    if not isinstance(token, str) or not token:
        raise AuthError("Session token is required.")
    with connect(database_path) as connection:
        _prune_expired_sessions(connection)
        row = connection.execute(
            """
            SELECT u.id AS id, u.username AS username, u.display_name AS display_name,
                   u.created_at AS created_at, u.updated_at AS updated_at,
                   s.expires_at AS expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
    if row is None:
        raise AuthError("Session is invalid or has expired.")
    user = _user_to_dict(row)
    user["sessionExpiresAt"] = row["expires_at"]
    return user


def delete_session(database_path: Path, token: str) -> bool:
    initialize_database(database_path)
    with connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM sessions WHERE token = ?", (token,)
        )
        return cursor.rowcount > 0


def list_user_sessions(
    database_path: Path, user_id: int
) -> list[dict[str, Any]]:
    initialize_database(database_path)
    with connect(database_path) as connection:
        _prune_expired_sessions(connection)
        rows = connection.execute(
            "SELECT token, created_at, expires_at FROM sessions WHERE user_id = ? "
            "ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [
        {
            "token": row["token"],
            "createdAt": row["created_at"],
            "expiresAt": row["expires_at"],
        }
        for row in rows
    ]


# --- Boards -----------------------------------------------------------------


def create_default_board(timestamp: str | None = None) -> dict[str, Any]:
    now = timestamp or utc_now()
    base_cards = {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
            "priority": "high",
            "labels": ["planning"],
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
            "priority": "medium",
            "labels": ["research"],
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
            "priority": "medium",
            "labels": ["design"],
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
            "priority": "low",
            "labels": ["ux"],
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
            "priority": "medium",
            "labels": ["design"],
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
            "priority": "low",
            "labels": ["qa"],
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
            "priority": "high",
            "labels": ["launch"],
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
            "priority": "medium",
            "labels": ["sprint"],
        },
    }
    cards = {
        card_id: _normalize_card(
            {
                **card,
                "createdAt": now,
                "updatedAt": now,
            }
        )
        for card_id, card in base_cards.items()
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
        "cards": cards,
    }


def _normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    """Ensure new optional fields exist with safe defaults."""
    normalized = dict(card)
    normalized.setdefault("priority", None)
    normalized.setdefault("dueDate", None)
    normalized.setdefault("labels", [])
    normalized.setdefault("assignee", None)
    if normalized["labels"] is None:
        normalized["labels"] = []
    return normalized


def normalize_board(board: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(board, dict):
        return board
    cards = board.get("cards")
    if isinstance(cards, dict):
        board = {
            **board,
            "cards": {
                card_id: _normalize_card(card)
                if isinstance(card, dict)
                else card
                for card_id, card in cards.items()
            },
        }
    return board


def _validate_priority(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str) or value not in ALLOWED_PRIORITIES:
        raise StorageError(
            "Card priority must be one of: " + ", ".join(sorted(ALLOWED_PRIORITIES))
        )


def _validate_due_date(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not DUE_DATE_PATTERN.match(value):
        raise StorageError("Card dueDate must be an ISO date string (YYYY-MM-DD).")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise StorageError("Card dueDate must be a valid calendar date.") from error


def _validate_labels(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise StorageError("Card labels must be a list of strings.")
    if len(value) > MAX_LABELS_PER_CARD:
        raise StorageError(
            f"Card labels must contain at most {MAX_LABELS_PER_CARD} entries."
        )
    for label in value:
        if not isinstance(label, str) or not label:
            raise StorageError("Each card label must be a non-empty string.")
        if len(label) > MAX_LABEL_LENGTH:
            raise StorageError(
                f"Card label must be {MAX_LABEL_LENGTH} characters or fewer."
            )


def _validate_assignee(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise StorageError("Card assignee must be a string or null.")
    if len(value) > MAX_USERNAME_LENGTH:
        raise StorageError(
            f"Card assignee must be {MAX_USERNAME_LENGTH} characters or fewer."
        )


def validate_board(board: Any) -> None:
    if not isinstance(board, dict):
        raise StorageError("Board must be an object.")
    if board.get("version") != 1:
        raise StorageError("Board version must be 1.")

    columns = board.get("columns")
    if not isinstance(columns, list) or not columns:
        raise StorageError("Board must include at least one column.")
    if len(columns) > MAX_COLUMNS:
        raise StorageError(f"Board may include at most {MAX_COLUMNS} columns.")

    cards = board.get("cards")
    if not isinstance(cards, dict):
        raise StorageError("Board cards must be an object.")
    if len(cards) > MAX_CARDS:
        raise StorageError(f"Board may include at most {MAX_CARDS} cards.")

    column_ids: set[str] = set()
    referenced_card_ids: list[str] = []

    for column in columns:
        if not isinstance(column, dict):
            raise StorageError("Each column must be an object.")
        column_id = column.get("id")
        if not isinstance(column_id, str) or not column_id:
            raise StorageError("Each column must have an id.")
        if len(column_id) > MAX_ID_LENGTH:
            raise StorageError(
                f"Column id must be {MAX_ID_LENGTH} characters or fewer."
            )
        if column_id in column_ids:
            raise StorageError("Column ids must be unique.")
        column_ids.add(column_id)
        title = column.get("title")
        if not isinstance(title, str):
            raise StorageError("Each column must have a title.")
        if len(title) > MAX_TITLE_LENGTH:
            raise StorageError(
                f"Column title must be {MAX_TITLE_LENGTH} characters or fewer."
            )
        card_ids = column.get("cardIds")
        if not isinstance(card_ids, list) or not all(
            isinstance(card_id, str) for card_id in card_ids
        ):
            raise StorageError("Each column must have cardIds as strings.")
        referenced_card_ids.extend(card_ids)

    if len(referenced_card_ids) != len(set(referenced_card_ids)):
        raise StorageError("A card can appear in only one column.")

    for card_id, card in cards.items():
        if not isinstance(card_id, str) or not isinstance(card, dict):
            raise StorageError("Each card must be keyed by id.")
        if len(card_id) > MAX_ID_LENGTH:
            raise StorageError(
                f"Card id must be {MAX_ID_LENGTH} characters or fewer."
            )
        if card.get("id") != card_id:
            raise StorageError("Card keys must match card ids.")
        title = card.get("title")
        if not isinstance(title, str):
            raise StorageError("Each card must have a title.")
        if len(title) > MAX_TITLE_LENGTH:
            raise StorageError(
                f"Card title must be {MAX_TITLE_LENGTH} characters or fewer."
            )
        details = card.get("details")
        if not isinstance(details, str):
            raise StorageError("Each card must have details.")
        if len(details) > MAX_DETAILS_LENGTH:
            raise StorageError(
                f"Card details must be {MAX_DETAILS_LENGTH} characters or fewer."
            )
        if not isinstance(card.get("createdAt"), str):
            raise StorageError("Each card must have createdAt.")
        if not isinstance(card.get("updatedAt"), str):
            raise StorageError("Each card must have updatedAt.")
        _validate_priority(card.get("priority"))
        _validate_due_date(card.get("dueDate"))
        _validate_labels(card.get("labels"))
        _validate_assignee(card.get("assignee"))

    referenced = set(referenced_card_ids)
    card_keys = set(cards.keys())
    missing = referenced - card_keys
    if missing:
        raise StorageError("Every cardIds entry must refer to an existing card.")
    if card_keys - referenced:
        raise StorageError("Every card must be assigned to a column.")


def _validate_board_title(title: Any) -> str:
    if not isinstance(title, str):
        raise StorageError("Board title must be a string.")
    cleaned = title.strip()
    if not cleaned:
        raise StorageError("Board title must not be empty.")
    if len(cleaned) > MAX_BOARD_TITLE_LENGTH:
        raise StorageError(
            f"Board title must be at most {MAX_BOARD_TITLE_LENGTH} characters."
        )
    return cleaned


def _validate_board_description(description: Any) -> str:
    if description is None:
        return ""
    if not isinstance(description, str):
        raise StorageError("Board description must be a string.")
    cleaned = description.strip()
    if len(cleaned) > MAX_BOARD_DESCRIPTION_LENGTH:
        raise StorageError(
            f"Board description must be at most {MAX_BOARD_DESCRIPTION_LENGTH} characters."
        )
    return cleaned


def _board_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "ownerId": int(row["owner_id"]),
        "title": row["title"],
        "description": row["description"] or "",
        "position": int(row["position"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def _board_full(row: sqlite3.Row) -> dict[str, Any]:
    summary = _board_summary(row)
    summary["data"] = json.loads(row["data"])
    return summary


def list_boards(database_path: Path, user_id: int) -> list[dict[str, Any]]:
    initialize_database(database_path)
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, owner_id, title, description, position, data, created_at, updated_at
            FROM boards WHERE owner_id = ?
            ORDER BY position ASC, created_at ASC
            """,
            (user_id,),
        ).fetchall()
    return [_board_summary(row) for row in rows]


def get_board(
    database_path: Path,
    user_id: int,
    board_id: int,
) -> dict[str, Any]:
    initialize_database(database_path)
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, owner_id, title, description, position, data, created_at, updated_at
            FROM boards WHERE id = ? AND owner_id = ?
            """,
            (board_id, user_id),
        ).fetchone()
    if row is None:
        raise NotFoundError("Board does not exist.")
    return _board_full(row)


def create_board(
    database_path: Path,
    user_id: int,
    title: str,
    description: str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initialize_database(database_path)
    cleaned_title = _validate_board_title(title)
    cleaned_description = _validate_board_description(description)
    now = utc_now()
    if data is None:
        board_data = create_default_board(now)
    else:
        board_data = normalize_board(data)
    validate_board(board_data)
    with connect(database_path) as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if existing is None:
            raise NotFoundError("User does not exist.")
        count = connection.execute(
            "SELECT COUNT(*) AS n FROM boards WHERE owner_id = ?",
            (user_id,),
        ).fetchone()
        if int(count["n"]) >= MAX_BOARDS_PER_USER:
            raise ConflictError(
                f"You may have at most {MAX_BOARDS_PER_USER} boards."
            )
        position_row = connection.execute(
            "SELECT COALESCE(MAX(position), -1) AS p FROM boards WHERE owner_id = ?",
            (user_id,),
        ).fetchone()
        next_position = int(position_row["p"]) + 1
        cursor = connection.execute(
            """
            INSERT INTO boards (owner_id, title, description, position, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                cleaned_title,
                cleaned_description,
                next_position,
                json.dumps(board_data, separators=(",", ":")),
                now,
                now,
            ),
        )
        board_id = int(cursor.lastrowid)
        row = connection.execute(
            """
            SELECT id, owner_id, title, description, position, data, created_at, updated_at
            FROM boards WHERE id = ?
            """,
            (board_id,),
        ).fetchone()
    return _board_full(row)


def update_board_meta(
    database_path: Path,
    user_id: int,
    board_id: int,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    initialize_database(database_path)
    fields: list[tuple[str, Any]] = []
    if title is not None:
        fields.append(("title", _validate_board_title(title)))
    if description is not None:
        fields.append(("description", _validate_board_description(description)))
    if not fields:
        return get_board(database_path, user_id, board_id)
    fields.append(("updated_at", utc_now()))
    set_clause = ", ".join(f"{name} = ?" for name, _ in fields)
    params = [value for _, value in fields] + [board_id, user_id]
    with connect(database_path) as connection:
        cursor = connection.execute(
            f"UPDATE boards SET {set_clause} WHERE id = ? AND owner_id = ?",
            params,
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Board does not exist.")
    return get_board(database_path, user_id, board_id)


def update_board_data(
    database_path: Path,
    user_id: int,
    board_id: int,
    data: dict[str, Any],
    expected_updated_at: str | None = None,
) -> dict[str, Any]:
    """Replace board JSON content. If expected_updated_at is set, raise
    ConflictError when the stored value differs (optimistic concurrency)."""
    initialize_database(database_path)
    normalized = normalize_board(data)
    validate_board(normalized)
    now = utc_now()
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT updated_at FROM boards WHERE id = ? AND owner_id = ?",
            (board_id, user_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("Board does not exist.")
        if expected_updated_at is not None and row["updated_at"] != expected_updated_at:
            raise ConflictError(
                "Board changed since you last loaded it. Please reload and retry."
            )
        connection.execute(
            "UPDATE boards SET data = ?, updated_at = ? WHERE id = ? AND owner_id = ?",
            (
                json.dumps(normalized, separators=(",", ":")),
                now,
                board_id,
                user_id,
            ),
        )
    return get_board(database_path, user_id, board_id)


def delete_board(database_path: Path, user_id: int, board_id: int) -> None:
    initialize_database(database_path)
    with connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM boards WHERE id = ? AND owner_id = ?",
            (board_id, user_id),
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Board does not exist.")


def reorder_boards(
    database_path: Path, user_id: int, board_ids: Iterable[int]
) -> list[dict[str, Any]]:
    initialize_database(database_path)
    ordered = list(board_ids)
    if len(ordered) != len(set(ordered)):
        raise StorageError("Board ordering must not contain duplicates.")
    now = utc_now()
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT id FROM boards WHERE owner_id = ?", (user_id,)
        ).fetchall()
        owned = {int(row["id"]) for row in rows}
        if owned != set(ordered):
            raise StorageError(
                "Board ordering must include exactly the user's existing board ids."
            )
        for index, board_id in enumerate(ordered):
            connection.execute(
                "UPDATE boards SET position = ?, updated_at = ? WHERE id = ?",
                (index, now, board_id),
            )
    return list_boards(database_path, user_id)
