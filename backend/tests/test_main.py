import json
from pathlib import Path
from typing import Callable

from fastapi.testclient import TestClient

from app.deepseek import DeepSeekAPIError, DeepSeekConfigurationError
from app.main import create_app
from app.storage import create_default_board, save_board


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


def test_index_serves_static_kanban_html(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<html><head><script src="/_next/static/app.js"></script></head>'
        "<body><h1>Kanban Studio</h1></body></html>",
        encoding="utf-8",
    )
    (tmp_path / "_next" / "static").mkdir(parents=True)
    (tmp_path / "_next" / "static" / "app.js").write_text(
        'console.log("kanban");',
        encoding="utf-8",
    )
    client = build_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Kanban Studio" in response.text
    assert "/_next/static/app.js" in response.text

    asset_response = client.get("/_next/static/app.js")
    assert asset_response.status_code == 200
    assert "kanban" in asset_response.text


def test_health_returns_ok() -> None:
    client = build_client(Path("unused"))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_board_api_creates_missing_database_and_default_board(tmp_path: Path) -> None:
    database_path = tmp_path / "app.db"
    client = build_client(Path("unused"), database_path)

    response = client.get("/api/board")

    assert response.status_code == 200
    assert database_path.exists()
    board = response.json()
    assert board["version"] == 1
    assert [column["id"] for column in board["columns"]] == [
        "col-backlog",
        "col-discovery",
        "col-progress",
        "col-review",
        "col-done",
    ]
    assert board["cards"]["card-1"]["createdAt"]


def test_board_api_updates_and_persists_board(tmp_path: Path) -> None:
    database_path = tmp_path / "app.db"
    client = build_client(Path("unused"), database_path)
    board = create_default_board("2026-01-01T00:00:00Z")
    board["columns"][0]["title"] = "Ideas"

    update_response = client.put("/api/board", json=board)
    assert update_response.status_code == 200

    next_client = build_client(Path("unused"), database_path)
    read_response = next_client.get("/api/board")

    assert read_response.status_code == 200
    assert read_response.json()["columns"][0]["title"] == "Ideas"


def test_board_api_rejects_invalid_board(tmp_path: Path) -> None:
    client = build_client(Path("unused"), tmp_path / "app.db")
    board = create_default_board("2026-01-01T00:00:00Z")
    board["columns"][0]["cardIds"].append("missing-card")

    response = client.put("/api/board", json=board)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Every cardIds entry must refer to an existing card."
    )


def test_deepseek_check_returns_mocked_answer() -> None:
    client = build_client(
        Path("unused"),
        deepseek_check=lambda: {"model": "deepseek-v4-pro", "answer": "4"},
    )

    response = client.get("/api/dev/deepseek-check")

    assert response.status_code == 200
    assert response.json() == {"model": "deepseek-v4-pro", "answer": "4"}


def test_deepseek_check_reports_missing_api_key() -> None:
    def missing_key() -> dict[str, str]:
        raise DeepSeekConfigurationError(
            "DEEPSEEK_API_KEY is not configured. Set it in the project root .env."
        )

    client = build_client(Path("unused"), deepseek_check=missing_key)

    response = client.get("/api/dev/deepseek-check")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "DEEPSEEK_API_KEY is not configured. Set it in the project root .env."
    )


def test_deepseek_check_reports_api_error() -> None:
    def api_error() -> dict[str, str]:
        raise DeepSeekAPIError("DeepSeek API request failed.")

    client = build_client(Path("unused"), deepseek_check=api_error)

    response = client.get("/api/dev/deepseek-check")

    assert response.status_code == 502
    assert response.json()["detail"] == "DeepSeek API request failed."


def test_ai_chat_returns_reply_without_board_update(tmp_path: Path) -> None:
    def ai_completion(messages: list[dict[str, str]]) -> str:
        assert any("Current Kanban board JSON" in message["content"] for message in messages)
        return json.dumps(
            {
                "assistantMessage": "Nothing to change.",
                "board": None,
                "operationSummary": None,
            }
        )

    client = build_client(
        Path("unused"),
        tmp_path / "app.db",
        ai_completion=ai_completion,
    )

    response = client.post(
        "/api/ai/chat",
        json={
            "message": "What is on my board?",
            "history": [{"role": "assistant", "content": "Ready."}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistantMessage"] == "Nothing to change."
    assert body["board"] is None
    assert body["history"] == [
        {"role": "assistant", "content": "Ready."},
        {"role": "user", "content": "What is on my board?"},
        {"role": "assistant", "content": "Nothing to change."},
    ]


def test_ai_chat_saves_valid_board_update(tmp_path: Path) -> None:
    database_path = tmp_path / "app.db"

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
        Path("unused"),
        database_path,
        ai_completion=ai_completion,
    )

    response = client.post("/api/ai/chat", json={"message": "Rename card one"})

    assert response.status_code == 200
    assert response.json()["board"]["cards"]["card-1"]["title"] == "AI edited title"
    assert client.get("/api/board").json()["cards"]["card-1"]["title"] == (
        "AI edited title"
    )


def test_ai_chat_rejects_update_when_board_changed_during_ai_call(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "app.db"

    def ai_completion(messages: list[dict[str, str]]) -> str:
        concurrent_board = create_default_board("2026-01-01T00:00:00Z")
        concurrent_board["columns"][0]["title"] = "Changed elsewhere"
        save_board(database_path, concurrent_board)

        ai_board = create_default_board("2026-01-01T00:00:00Z")
        ai_board["cards"]["card-1"]["title"] = "AI edited title"
        return json.dumps(
            {
                "assistantMessage": "Updated the card.",
                "board": ai_board,
                "operationSummary": "Renamed card-1.",
            }
        )

    client = build_client(
        Path("unused"),
        database_path,
        ai_completion=ai_completion,
    )

    response = client.post("/api/ai/chat", json={"message": "Rename card one"})

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Board changed while the AI was responding. Please retry the request."
    )
    saved_board = client.get("/api/board").json()
    assert saved_board["columns"][0]["title"] == "Changed elsewhere"
    assert saved_board["cards"]["card-1"]["title"] == "Align roadmap themes"


def test_ai_chat_rejects_invalid_ai_board_without_saving(tmp_path: Path) -> None:
    database_path = tmp_path / "app.db"

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
        Path("unused"),
        database_path,
        ai_completion=ai_completion,
    )
    original_title = client.get("/api/board").json()["cards"]["card-1"]["title"]

    response = client.post("/api/ai/chat", json={"message": "Create a broken update"})

    assert response.status_code == 502
    assert "AI board update is invalid" in response.json()["detail"]
    assert client.get("/api/board").json()["cards"]["card-1"]["title"] == original_title


def test_ai_chat_rejects_invalid_request(tmp_path: Path) -> None:
    client = build_client(Path("unused"), tmp_path / "app.db")

    response = client.post("/api/ai/chat", json={"message": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Message must be a non-empty string."
