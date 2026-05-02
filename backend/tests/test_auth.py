from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.storage import (
    AuthError,
    ConflictError,
    NotFoundError,
    StorageError,
    authenticate,
    change_password,
    create_session,
    create_user,
    delete_session,
    get_user,
    hash_password,
    list_user_sessions,
    resolve_session,
    update_user_profile,
    verify_password,
    MVP_PASSWORD,
    MVP_USERNAME,
)


def db_path(tmp_path: Path) -> Path:
    return tmp_path / "app.db"


# --- password hashing ------------------------------------------------------


def test_hash_password_returns_verifiable_string() -> None:
    digest = hash_password("plain-text-password")
    assert digest.startswith("scrypt$")
    assert verify_password("plain-text-password", digest) is True
    assert verify_password("wrong-password", digest) is False


def test_hash_password_uses_unique_salt() -> None:
    a = hash_password("same-password-1")
    b = hash_password("same-password-1")
    assert a != b


def test_hash_password_rejects_short_password() -> None:
    with pytest.raises(StorageError, match="at least"):
        hash_password("short")


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password("anything", "not-a-real-hash") is False
    assert verify_password("anything", "scrypt$bad$1$1$AAAA$AAAA") is False


# --- user lifecycle ---------------------------------------------------------


def test_create_user_seeds_default_board(tmp_path: Path) -> None:
    user = create_user(
        db_path(tmp_path), "alice", "alice-secret-1", "Alice"
    )
    assert user["username"] == "alice"
    assert user["displayName"] == "Alice"
    assert isinstance(user["id"], int)


def test_create_user_rejects_duplicate_username(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    create_user(path, "alice", "alice-secret-1")
    with pytest.raises(ConflictError):
        create_user(path, "alice", "alice-secret-2")


def test_create_user_rejects_invalid_username(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    with pytest.raises(StorageError):
        create_user(path, "ab", "long-enough-1")
    with pytest.raises(StorageError):
        create_user(path, "has spaces", "long-enough-1")


def test_authenticate_returns_user_for_valid_credentials(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    assert user["username"] == MVP_USERNAME


def test_authenticate_raises_for_invalid_credentials(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    with pytest.raises(AuthError):
        authenticate(path, MVP_USERNAME, "wrong-password")


def test_authenticate_is_case_insensitive_for_username(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME.upper(), MVP_PASSWORD)
    assert user["username"] == MVP_USERNAME


def test_update_user_profile_changes_display_name(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    updated = update_user_profile(path, user["id"], "Renamed")
    assert updated["displayName"] == "Renamed"
    refreshed = get_user(path, user["id"])
    assert refreshed["displayName"] == "Renamed"


def test_change_password_invalidates_sessions(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    session = create_session(path, user["id"])

    change_password(path, user["id"], MVP_PASSWORD, "different-pw-1")

    with pytest.raises(AuthError):
        resolve_session(path, session["token"])

    refreshed = authenticate(path, MVP_USERNAME, "different-pw-1")
    assert refreshed["id"] == user["id"]


def test_change_password_rejects_wrong_current(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    with pytest.raises(AuthError):
        change_password(path, user["id"], "wrong", "new-strong-pw-1")


# --- sessions ---------------------------------------------------------------


def test_create_session_returns_unique_token(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    a = create_session(path, user["id"])
    b = create_session(path, user["id"])
    assert a["token"] != b["token"]


def test_resolve_session_returns_user(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    session = create_session(path, user["id"])
    resolved = resolve_session(path, session["token"])
    assert resolved["username"] == MVP_USERNAME
    assert resolved["sessionExpiresAt"] == session["expiresAt"]


def test_resolve_session_rejects_unknown_token(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    with pytest.raises(AuthError):
        resolve_session(path, "no-such-token")


def test_resolve_session_rejects_expired_token(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    expired = create_session(path, user["id"], ttl_seconds=1)
    time.sleep(1.5)
    with pytest.raises(AuthError):
        resolve_session(path, expired["token"])


def test_delete_session_invalidates_token(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    session = create_session(path, user["id"])
    assert delete_session(path, session["token"]) is True
    with pytest.raises(AuthError):
        resolve_session(path, session["token"])


def test_list_user_sessions_orders_by_most_recent_first(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    user = authenticate(path, MVP_USERNAME, MVP_PASSWORD)
    create_session(path, user["id"])
    create_session(path, user["id"])
    sessions = list_user_sessions(path, user["id"])
    assert len(sessions) == 2


def test_create_session_rejects_unknown_user(tmp_path: Path) -> None:
    path = db_path(tmp_path)
    with pytest.raises(NotFoundError):
        create_session(path, 9999)
