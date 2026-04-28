from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def build_client(static_dir: Path) -> TestClient:
    return TestClient(create_app(static_dir))


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
