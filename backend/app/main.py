from pathlib import Path
from typing import Any, Callable

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.ai import (
    AIResponseError,
    ask_ai_for_board_update,
    validate_history,
    validate_user_message,
)
from app.deepseek import (
    DeepSeekAPIError,
    DeepSeekConfigurationError,
    run_connectivity_check,
)
from app.storage import get_database_path, get_or_create_board, save_board

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


def create_app(
    static_dir: Path = STATIC_DIR,
    database_path: Path | None = None,
    deepseek_check: Callable[[], dict[str, str]] | None = None,
    ai_completion: Callable[[list[dict[str, str]]], str] | None = None,
) -> FastAPI:
    app = FastAPI(title="Project Management MVP")
    db_path = database_path or get_database_path()
    deepseek_check_fn = deepseek_check or run_connectivity_check
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

    @app.post("/api/ai/chat")
    def ai_chat(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            user_message = validate_user_message(payload.get("message"))
            history = validate_history(payload.get("history", []))
            current_board = get_or_create_board(db_path)
            ai_response = ask_ai_for_board_update(
                current_board,
                user_message,
                history,
                ai_completion,
            )
            updated_board = ai_response["board"]
            if updated_board is not None:
                save_board(db_path, updated_board)

            next_history = [
                *history,
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": ai_response["assistantMessage"]},
            ]
            return {
                "assistantMessage": ai_response["assistantMessage"],
                "board": updated_board,
                "operationSummary": ai_response["operationSummary"],
                "history": next_history,
            }
        except AIResponseError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except DeepSeekConfigurationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except DeepSeekAPIError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @app.get("/api/dev/deepseek-check")
    def check_deepseek() -> dict[str, str]:
        try:
            return deepseek_check_fn()
        except DeepSeekConfigurationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except DeepSeekAPIError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    return app


app = create_app()
