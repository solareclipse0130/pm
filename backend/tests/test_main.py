from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.storage import create_default_board


def build_client(static_dir: Path, database_path: Path | None = None) -> TestClient:
    return TestClient(create_app(static_dir, database_path))


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
