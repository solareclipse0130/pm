from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.storage import get_database_path, get_or_create_board, save_board

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


def create_app(
    static_dir: Path = STATIC_DIR,
    database_path: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Project Management MVP")
    db_path = database_path or get_database_path()
    app.mount(
        "/_next",
        StaticFiles(directory=static_dir / "_next", check_dir=False),
        name="next-static",
    )

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html", media_type="text/html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(static_dir / "favicon.ico")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/board")
    def read_board() -> dict[str, Any]:
        return get_or_create_board(db_path)

    @app.put("/api/board")
    def update_board(board: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            return save_board(db_path, board)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    return app


app = create_app()
