from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient

from app.deepseek import DeepSeekAPIError, DeepSeekConfigurationError
from app.main import create_app
from app.storage import MVP_PASSWORD, MVP_USERNAME, create_default_board


def build_client(
    static_dir: Path,
    database_path: Path | None = None,
    deepseek_check: Callable[[], dict[str, str]] | None = None,
    ai_completion: Callable[[list[dict[str, str]]], str] | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            static_dir,
            database_path,
            deepseek_check=deepseek_check,
            ai_completion=ai_completion,
        )
    )


def login_mvp(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": MVP_USERNAME, "password": MVP_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["session"]["token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Static / health --------------------------------------------------------


def test_index_serves_static_kanban_html(tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(
        '<html><head><script src="/_next/static/app.js"></script></head>'
        "<body><h1>Kanban Studio</h1></body></html>",
        encoding="utf-8",
    )
    (static_dir / "_next" / "static").mkdir(parents=True)
    (static_dir / "_next" / "static" / "app.js").write_text(
        'console.log("kanban");',
        encoding="utf-8",
    )
    client = build_client(static_dir, tmp_path / "app.db")

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Kanban Studio" in response.text

    asset_response = client.get("/_next/static/app.js")
    assert asset_response.status_code == 200
    assert "kanban" in asset_response.text


def test_health_returns_ok(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Auth -------------------------------------------------------------------


def test_signup_creates_user_and_returns_session(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")

    response = client.post(
        "/api/auth/signup",
        json={
            "username": "alice",
            "password": "wonderland-9",
            "displayName": "Alice",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["username"] == "alice"
    assert body["user"]["displayName"] == "Alice"
    assert body["session"]["token"]
    assert body["session"]["expiresAt"]


def test_signup_rejects_duplicate_username(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    payload = {"username": "alice", "password": "secret-12"}

    first = client.post("/api/auth/signup", json=payload)
    assert first.status_code == 201
    second = client.post("/api/auth/signup", json=payload)

    assert second.status_code == 409
    assert "already taken" in second.json()["detail"]


def test_signup_rejects_weak_password(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    response = client.post(
        "/api/auth/signup", json={"username": "bob", "password": "short"}
    )
    assert response.status_code == 400
    assert "at least" in response.json()["detail"]


def test_signup_rejects_invalid_username(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    response = client.post(
        "/api/auth/signup", json={"username": "ab", "password": "long-enough-9"}
    )
    assert response.status_code == 400


def test_login_succeeds_for_mvp_user(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    response = client.post(
        "/api/auth/login",
        json={"username": MVP_USERNAME, "password": MVP_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == MVP_USERNAME
    assert body["session"]["token"]


def test_login_rejects_bad_credentials(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    response = client.post(
        "/api/auth/login",
        json={"username": MVP_USERNAME, "password": "wrong-password-1"},
    )
    assert response.status_code == 401


def test_me_returns_current_user(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    response = client.get("/api/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == MVP_USERNAME


def test_me_requires_auth(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_rejects_invalid_token(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    response = client.get("/api/auth/me", headers=auth_headers("not-a-token"))
    assert response.status_code == 401


def test_logout_invalidates_session(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    logout_response = client.post(
        "/api/auth/logout", headers=auth_headers(token)
    )
    assert logout_response.status_code == 200
    assert logout_response.json() == {"loggedOut": True}

    follow_up = client.get("/api/auth/me", headers=auth_headers(token))
    assert follow_up.status_code == 401


def test_change_password_requires_current_password(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    response = client.put(
        "/api/auth/password",
        json={"currentPassword": "wrong-password", "newPassword": "new-secret-1"},
        headers=auth_headers(token),
    )
    assert response.status_code == 401


def test_change_password_invalidates_existing_sessions(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    response = client.put(
        "/api/auth/password",
        json={"currentPassword": MVP_PASSWORD, "newPassword": "newer-secret-1"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    follow_up = client.get("/api/auth/me", headers=auth_headers(token))
    assert follow_up.status_code == 401

    relogin = client.post(
        "/api/auth/login",
        json={"username": MVP_USERNAME, "password": "newer-secret-1"},
    )
    assert relogin.status_code == 200


def test_update_profile_changes_display_name(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    response = client.put(
        "/api/auth/profile",
        json={"displayName": "Renamed"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["displayName"] == "Renamed"


def test_list_user_sessions_returns_active_token(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    response = client.get(
        "/api/auth/sessions", headers=auth_headers(token)
    )
    assert response.status_code == 200
    sessions = response.json()
    assert any(item["token"] == token for item in sessions)


# --- Boards -----------------------------------------------------------------


def test_list_boards_returns_seeded_default(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    response = client.get("/api/boards", headers=auth_headers(token))
    assert response.status_code == 200
    boards = response.json()
    assert len(boards) == 1
    assert boards[0]["title"] == "My Board"


def test_create_board_appends_to_user_collection(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    response = client.post(
        "/api/boards",
        json={"title": "Marketing", "description": "Q3 plans"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["title"] == "Marketing"
    assert created["description"] == "Q3 plans"
    assert created["data"]["version"] == 1

    list_response = client.get("/api/boards", headers=auth_headers(token))
    titles = [board["title"] for board in list_response.json()]
    assert "My Board" in titles
    assert "Marketing" in titles


def test_get_board_returns_404_when_not_owned(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    mvp_token = login_mvp(client)
    mvp_boards = client.get("/api/boards", headers=auth_headers(mvp_token)).json()
    mvp_board_id = mvp_boards[0]["id"]

    signup = client.post(
        "/api/auth/signup",
        json={"username": "carol", "password": "carol-secret-1"},
    )
    carol_token = signup.json()["session"]["token"]

    response = client.get(
        f"/api/boards/{mvp_board_id}", headers=auth_headers(carol_token)
    )
    assert response.status_code == 404


def test_patch_board_updates_title_only(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    boards = client.get("/api/boards", headers=auth_headers(token)).json()
    board_id = boards[0]["id"]

    response = client.patch(
        f"/api/boards/{board_id}",
        json={"title": "Renamed Board"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed Board"


def test_put_board_data_persists_full_board(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    boards = client.get("/api/boards", headers=auth_headers(token)).json()
    board_id = boards[0]["id"]
    original = client.get(
        f"/api/boards/{board_id}", headers=auth_headers(token)
    ).json()

    new_data = original["data"]
    new_data["columns"][0]["title"] = "Inbox"
    new_data["cards"]["card-1"]["priority"] = "urgent"
    new_data["cards"]["card-1"]["labels"] = ["sprint", "priority"]

    response = client.put(
        f"/api/boards/{board_id}/data",
        json={"data": new_data},
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["data"]["columns"][0]["title"] == "Inbox"
    assert updated["data"]["cards"]["card-1"]["priority"] == "urgent"
    assert updated["data"]["cards"]["card-1"]["labels"] == ["sprint", "priority"]


def test_put_board_data_rejects_invalid_payload(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    boards = client.get("/api/boards", headers=auth_headers(token)).json()
    board_id = boards[0]["id"]
    data = client.get(
        f"/api/boards/{board_id}", headers=auth_headers(token)
    ).json()["data"]
    data["columns"][0]["cardIds"].append("missing-card")

    response = client.put(
        f"/api/boards/{board_id}/data",
        json={"data": data},
        headers=auth_headers(token),
    )
    assert response.status_code == 400


def test_put_board_data_optimistic_concurrency(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    boards = client.get("/api/boards", headers=auth_headers(token)).json()
    board_id = boards[0]["id"]
    original = client.get(
        f"/api/boards/{board_id}", headers=auth_headers(token)
    ).json()

    bumped = original["data"]
    bumped["columns"][0]["title"] = "Inbox"
    client.put(
        f"/api/boards/{board_id}/data",
        json={"data": bumped},
        headers=auth_headers(token),
    )

    stale_data = original["data"]
    stale_data["columns"][1]["title"] = "Stale"
    response = client.put(
        f"/api/boards/{board_id}/data",
        json={"data": stale_data, "expectedUpdatedAt": original["updatedAt"]},
        headers=auth_headers(token),
    )
    assert response.status_code == 409


def test_delete_board_removes_it(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    create_response = client.post(
        "/api/boards",
        json={"title": "Throwaway"},
        headers=auth_headers(token),
    )
    board_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/boards/{board_id}", headers=auth_headers(token)
    )
    assert delete_response.status_code == 204

    list_after = client.get("/api/boards", headers=auth_headers(token)).json()
    assert all(b["id"] != board_id for b in list_after)


def test_reorder_boards_updates_position(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    second = client.post(
        "/api/boards",
        json={"title": "Second"},
        headers=auth_headers(token),
    ).json()
    third = client.post(
        "/api/boards",
        json={"title": "Third"},
        headers=auth_headers(token),
    ).json()

    boards = client.get("/api/boards", headers=auth_headers(token)).json()
    ids = [board["id"] for board in boards]
    new_order = [third["id"], second["id"], ids[0]]
    response = client.put(
        "/api/boards/order",
        json={"boardIds": new_order},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert [board["id"] for board in response.json()] == new_order


def test_unauthorized_user_cannot_modify_others_board(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    mvp_token = login_mvp(client)
    target = client.get("/api/boards", headers=auth_headers(mvp_token)).json()[0]

    signup = client.post(
        "/api/auth/signup",
        json={"username": "eve", "password": "eve-secret-1"},
    )
    eve_token = signup.json()["session"]["token"]

    full_target = client.get(
        f"/api/boards/{target['id']}", headers=auth_headers(mvp_token)
    ).json()
    response = client.put(
        f"/api/boards/{target['id']}/data",
        json={"data": full_target["data"]},
        headers=auth_headers(eve_token),
    )
    assert response.status_code == 404


# --- AI chat (board-scoped) -------------------------------------------------


def test_ai_chat_returns_reply_without_board_update(tmp_path: Path) -> None:
    def ai_completion(messages: list[dict[str, str]]) -> str:
        assert any(
            "Current Kanban board JSON" in message["content"] for message in messages
        )
        return json.dumps(
            {
                "assistantMessage": "Nothing to change.",
                "board": None,
                "operationSummary": None,
            }
        )

    client = build_client(
        tmp_path / "static",
        tmp_path / "app.db",
        ai_completion=ai_completion,
    )
    token = login_mvp(client)
    boards = client.get("/api/boards", headers=auth_headers(token)).json()
    board_id = boards[0]["id"]

    response = client.post(
        f"/api/boards/{board_id}/ai/chat",
        json={
            "message": "What is on my board?",
            "history": [{"role": "assistant", "content": "Ready."}],
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistantMessage"] == "Nothing to change."
    assert body["board"] is None
    assert body["history"] == [
        {"role": "assistant", "content": "Ready."},
        {"role": "user", "content": "What is on my board?"},
        {"role": "assistant", "content": "Nothing to change."},
    ]


def test_ai_chat_saves_valid_board_update(tmp_path: Path) -> None:
    def ai_completion(messages: list[dict[str, str]]) -> str:
        board = create_default_board("2026-01-01T00:00:00Z")
        board["cards"]["card-1"]["title"] = "AI edited title"
        return json.dumps(
            {
                "assistantMessage": "Updated the card.",
                "board": board,
                "operationSummary": "Renamed card-1.",
            }
        )

    client = build_client(
        tmp_path / "static",
        tmp_path / "app.db",
        ai_completion=ai_completion,
    )
    token = login_mvp(client)
    board_id = client.get("/api/boards", headers=auth_headers(token)).json()[0]["id"]

    response = client.post(
        f"/api/boards/{board_id}/ai/chat",
        json={"message": "Rename card one"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    assert (
        response.json()["board"]["data"]["cards"]["card-1"]["title"]
        == "AI edited title"
    )
    follow_up = client.get(
        f"/api/boards/{board_id}", headers=auth_headers(token)
    ).json()
    assert follow_up["data"]["cards"]["card-1"]["title"] == "AI edited title"


def test_ai_chat_rejects_when_board_changes_mid_flight(tmp_path: Path) -> None:
    db_path = tmp_path / "app.db"
    static_dir = tmp_path / "static"

    state: dict[str, Any] = {}

    def ai_completion(messages: list[dict[str, str]]) -> str:
        # Simulate a concurrent write by hitting the API while the AI thinks.
        mid_token = state["token"]
        board_id = state["board_id"]
        current = state["client"].get(
            f"/api/boards/{board_id}", headers=auth_headers(mid_token)
        ).json()["data"]
        current["columns"][0]["title"] = "Changed elsewhere"
        state["client"].put(
            f"/api/boards/{board_id}/data",
            json={"data": current},
            headers=auth_headers(mid_token),
        )
        ai_board = create_default_board("2026-01-01T00:00:00Z")
        ai_board["cards"]["card-1"]["title"] = "AI edited title"
        return json.dumps(
            {
                "assistantMessage": "Updated the card.",
                "board": ai_board,
                "operationSummary": "Renamed card-1.",
            }
        )

    background_client = build_client(static_dir, db_path)
    background_token = login_mvp(background_client)
    background_board_id = (
        background_client.get(
            "/api/boards", headers=auth_headers(background_token)
        ).json()[0]["id"]
    )
    state.update(
        {
            "client": background_client,
            "token": background_token,
            "board_id": background_board_id,
        }
    )

    client = build_client(static_dir, db_path, ai_completion=ai_completion)
    token = login_mvp(client)
    board_id = client.get("/api/boards", headers=auth_headers(token)).json()[0]["id"]

    response = client.post(
        f"/api/boards/{board_id}/ai/chat",
        json={"message": "Rename card one"},
        headers=auth_headers(token),
    )
    assert response.status_code == 409
    follow_up = client.get(
        f"/api/boards/{board_id}", headers=auth_headers(token)
    ).json()
    assert follow_up["data"]["columns"][0]["title"] == "Changed elsewhere"
    assert (
        follow_up["data"]["cards"]["card-1"]["title"] == "Align roadmap themes"
    )


def test_ai_chat_rejects_invalid_ai_board_without_saving(tmp_path: Path) -> None:
    def ai_completion(messages: list[dict[str, str]]) -> str:
        board = create_default_board("2026-01-01T00:00:00Z")
        board["columns"][0]["cardIds"].append("missing-card")
        return json.dumps(
            {
                "assistantMessage": "Updated the board.",
                "board": board,
                "operationSummary": None,
            }
        )

    client = build_client(
        tmp_path / "static",
        tmp_path / "app.db",
        ai_completion=ai_completion,
    )
    token = login_mvp(client)
    board_id = client.get("/api/boards", headers=auth_headers(token)).json()[0]["id"]
    original_title = client.get(
        f"/api/boards/{board_id}", headers=auth_headers(token)
    ).json()["data"]["cards"]["card-1"]["title"]

    response = client.post(
        f"/api/boards/{board_id}/ai/chat",
        json={"message": "Create a broken update"},
        headers=auth_headers(token),
    )
    assert response.status_code == 502
    assert "AI board update is invalid" in response.json()["detail"]
    assert (
        client.get(f"/api/boards/{board_id}", headers=auth_headers(token)).json()[
            "data"
        ]["cards"]["card-1"]["title"]
        == original_title
    )


def test_ai_chat_rejects_invalid_request(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    token = login_mvp(client)
    board_id = client.get("/api/boards", headers=auth_headers(token)).json()[0]["id"]

    response = client.post(
        f"/api/boards/{board_id}/ai/chat",
        json={"message": "   "},
        headers=auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Message must be a non-empty string."


def test_ai_chat_requires_auth(tmp_path: Path) -> None:
    client = build_client(tmp_path / "static", tmp_path / "app.db")
    response = client.post("/api/boards/1/ai/chat", json={"message": "Hi"})
    assert response.status_code == 401


# --- DeepSeek connectivity check -------------------------------------------


def test_deepseek_check_reports_configuration_error(tmp_path: Path) -> None:
    def configuration_error() -> dict[str, str]:
        raise DeepSeekConfigurationError("DEEPSEEK_API_KEY is not configured.")

    client = build_client(
        tmp_path / "static",
        tmp_path / "app.db",
        deepseek_check=configuration_error,
    )
    response = client.get("/api/dev/deepseek-check")
    assert response.status_code == 503


def test_deepseek_check_reports_api_error(tmp_path: Path) -> None:
    def api_error() -> dict[str, str]:
        raise DeepSeekAPIError("DeepSeek API request failed.")

    client = build_client(
        tmp_path / "static",
        tmp_path / "app.db",
        deepseek_check=api_error,
    )
    response = client.get("/api/dev/deepseek-check")
    assert response.status_code == 502
    assert response.json()["detail"] == "DeepSeek API request failed."


def test_deepseek_check_returns_payload(tmp_path: Path) -> None:
    def successful() -> dict[str, str]:
        return {"model": "deepseek-v4-pro", "answer": "4"}

    client = build_client(
        tmp_path / "static",
        tmp_path / "app.db",
        deepseek_check=successful,
    )
    response = client.get("/api/dev/deepseek-check")
    assert response.status_code == 200
    assert response.json() == {"model": "deepseek-v4-pro", "answer": "4"}
