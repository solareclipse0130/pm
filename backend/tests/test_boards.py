from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.storage import (
    ConflictError,
    MAX_BOARDS_PER_USER,
    MVP_PASSWORD,
    MVP_USERNAME,
    NotFoundError,
    SCHEMA_VERSION,
    StorageError,
    authenticate,
    create_board,
    create_default_board,
    create_user,
    delete_board,
    get_board,
    initialize_database,
    list_boards,
    normalize_board,
    reorder_boards,
    update_board_data,
    update_board_meta,
)


def db_path(tmp_path: Path) -> Path:
    return tmp_path / "app.db"


def mvp_user_id(path: Path) -> int:
    return authenticate(path, MVP_USERNAME, MVP_PASSWORD)["id"]


def test_initialize_database_seeds_mvp_user_and_default_board(
    tmp_path: Path,
) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    boards = list_boards(path, user_id)
    assert len(boards) == 1
    full = get_board(path, user_id, boards[0]["id"])
    assert full["data"]["columns"][0]["title"] == "Backlog"
    assert full["data"]["cards"]["card-1"]["priority"] == "high"
    assert "planning" in full["data"]["cards"]["card-1"]["labels"]


def test_initialize_database_records_schema_version(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    initialize_database(path)
    with sqlite3.connect(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_create_board_appends_with_increasing_position(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    second = create_board(path, user_id, "Second", "Notes")
    third = create_board(path, user_id, "Third")
    boards = list_boards(path, user_id)
    positions = [board["position"] for board in boards]
    assert positions == sorted(positions)
    assert second["position"] < third["position"]


def test_create_board_rejects_empty_title(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    with pytest.raises(StorageError):
        create_board(path, user_id, "   ")


def test_create_board_rejects_unknown_user(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    with pytest.raises(NotFoundError):
        create_board(path, 9999, "Anything")


def test_create_board_enforces_per_user_limit(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    # default seed already creates one board
    for index in range(MAX_BOARDS_PER_USER - 1):
        create_board(path, user_id, f"Board {index}")
    with pytest.raises(ConflictError):
        create_board(path, user_id, "One Too Many")


def test_get_board_isolates_users(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    mvp_id = mvp_user_id(path)
    other = create_user(path, "carol", "carol-secret-1")
    target = list_boards(path, mvp_id)[0]
    with pytest.raises(NotFoundError):
        get_board(path, other["id"], target["id"])


def test_update_board_meta_updates_only_provided_fields(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    board = list_boards(path, user_id)[0]
    updated = update_board_meta(
        path, user_id, board["id"], description="New description"
    )
    assert updated["description"] == "New description"
    assert updated["title"] == board["title"]


def test_update_board_data_normalizes_card_extensions(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    board = list_boards(path, user_id)[0]
    full = get_board(path, user_id, board["id"])
    data = full["data"]
    # Strip optional fields then re-save: normalize_board should restore them.
    data["cards"]["card-1"].pop("priority")
    data["cards"]["card-1"].pop("labels")
    saved = update_board_data(path, user_id, board["id"], data)
    assert saved["data"]["cards"]["card-1"]["priority"] is None
    assert saved["data"]["cards"]["card-1"]["labels"] == []


def test_update_board_data_optimistic_concurrency(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    board = list_boards(path, user_id)[0]
    full = get_board(path, user_id, board["id"])
    stale_updated_at = full["updatedAt"]

    refreshed = full["data"]
    refreshed["columns"][0]["title"] = "Renamed"
    update_board_data(path, user_id, board["id"], refreshed)

    other = full["data"]
    other["columns"][0]["title"] = "Should Fail"
    with pytest.raises(ConflictError):
        update_board_data(
            path,
            user_id,
            board["id"],
            other,
            expected_updated_at=stale_updated_at,
        )


def test_delete_board_removes_only_target(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    extra = create_board(path, user_id, "Extra")
    delete_board(path, user_id, extra["id"])
    assert all(board["id"] != extra["id"] for board in list_boards(path, user_id))


def test_delete_board_unknown_id_raises(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    with pytest.raises(NotFoundError):
        delete_board(path, user_id, 999999)


def test_reorder_boards_requires_full_set(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    second = create_board(path, user_id, "Second")
    boards = list_boards(path, user_id)
    incomplete = [boards[0]["id"]]
    with pytest.raises(StorageError):
        reorder_boards(path, user_id, incomplete)


def test_reorder_boards_persists_new_order(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user_id = mvp_user_id(path)
    create_board(path, user_id, "Second")
    create_board(path, user_id, "Third")
    boards = list_boards(path, user_id)
    reversed_ids = list(reversed([board["id"] for board in boards]))
    reordered = reorder_boards(path, user_id, reversed_ids)
    assert [board["id"] for board in reordered] == reversed_ids


def test_normalize_board_fills_card_extensions() -> None:
    base = create_default_board("2026-01-01T00:00:00Z")
    bare = {
        "version": 1,
        "columns": base["columns"],
        "cards": {
            card_id: {
                "id": card["id"],
                "title": card["title"],
                "details": card["details"],
                "createdAt": card["createdAt"],
                "updatedAt": card["updatedAt"],
            }
            for card_id, card in base["cards"].items()
        },
    }
    normalized = normalize_board(bare)
    sample = next(iter(normalized["cards"].values()))
    assert sample["priority"] is None
    assert sample["labels"] == []
    assert sample["assignee"] is None
    assert sample["dueDate"] is None


# --- Migration of legacy schema --------------------------------------------


def test_initialize_database_migrates_legacy_single_board_schema(
    tmp_path: Path,
) -> None:
    path = db_path(tmp_path)
    # Build a database in the legacy v0 layout (no password_hash, unique user_id).
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE boards (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL UNIQUE,
              data TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            INSERT INTO users (username, created_at, updated_at)
            VALUES ('legacy', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
            """
        )
        cursor = connection.execute(
            "SELECT id FROM users WHERE username='legacy'"
        )
        user_id = cursor.fetchone()[0]
        legacy_board = {
            "version": 1,
            "columns": [
                {"id": "col-a", "title": "A", "cardIds": ["card-1"]},
            ],
            "cards": {
                "card-1": {
                    "id": "card-1",
                    "title": "Legacy",
                    "details": "Stored before migration.",
                    "createdAt": "2026-01-01T00:00:00Z",
                    "updatedAt": "2026-01-01T00:00:00Z",
                }
            },
        }
        connection.execute(
            "INSERT INTO boards (user_id, data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (
                user_id,
                json.dumps(legacy_board),
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )

    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert "sessions" in names
        legacy_id = connection.execute(
            "SELECT id FROM users WHERE username='legacy'"
        ).fetchone()["id"]
        # boards.owner_id replaces the old user_id column
        owner_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(boards)").fetchall()
        }
        assert "owner_id" in owner_columns
        assert "user_id" not in owner_columns
        boards = connection.execute(
            "SELECT data FROM boards WHERE owner_id = ?", (legacy_id,)
        ).fetchall()
        assert len(boards) == 1
        normalized = json.loads(boards[0]["data"])
        # Migration normalized card extensions.
        assert normalized["cards"]["card-1"]["labels"] == []
