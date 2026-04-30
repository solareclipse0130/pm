import inspect
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal, Union

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
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
from app.storage import (
    get_or_create_board,
    initialize_database,
    get_database_path,
    save_board,
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

DeepSeekCheckResult = Union[dict[str, str], Awaitable[dict[str, str]]]
DeepSeekCheckFn = Callable[[], DeepSeekCheckResult]
AICompletionResult = Union[str, Awaitable[str]]
AICompletionFn = Callable[[list[dict[str, str]]], AICompletionResult]


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class AiChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    history: list[ChatHistoryItem] = Field(default_factory=list)


class BoardCardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    details: str
    createdAt: str
    updatedAt: str


class BoardColumnPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    cardIds: list[str]


class BoardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    columns: list[BoardColumnPayload]
    cards: dict[str, BoardCardPayload]


def create_app(
    static_dir: Path = STATIC_DIR,
    database_path: Path | None = None,
    deepseek_check: DeepSeekCheckFn | None = None,
    ai_completion: AICompletionFn | None = None,
) -> FastAPI:
    app = FastAPI(title="Project Management MVP")
    db_path = database_path or get_database_path()
    initialize_database(db_path)
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
    def update_board(board: BoardPayload) -> dict[str, Any]:
        try:
            return save_board(db_path, board.model_dump())
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/api/ai/chat")
    async def ai_chat(payload: AiChatRequest = Body(...)) -> dict[str, Any]:
        try:
            user_message = validate_user_message(payload.message)
            history = validate_history(
                [item.model_dump() for item in payload.history]
            )
            current_board = get_or_create_board(db_path)
            ai_response = await ask_ai_for_board_update(
                current_board,
                user_message,
                history,
                ai_completion,
            )
            updated_board = ai_response["board"]
            if updated_board is not None:
                latest_board = get_or_create_board(db_path)
                if latest_board != current_board:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Board changed while the AI was responding. "
                            "Please retry the request."
                        ),
                    )
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
            raise HTTPException(status_code=503, detail=str(error)) from error
        except DeepSeekAPIError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @app.get("/api/dev/deepseek-check")
    async def check_deepseek() -> dict[str, str]:
        try:
            result = deepseek_check_fn()
            if inspect.isawaitable(result):
                result = await result
            return result
        except DeepSeekConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except DeepSeekAPIError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    return app


app = create_app()
