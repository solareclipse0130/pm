from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal, Union

from fastapi import Body, Depends, FastAPI, Header, HTTPException, status
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
    AuthError,
    ConflictError,
    NotFoundError,
    StorageError,
    authenticate,
    change_password,
    create_board,
    create_session,
    create_user,
    delete_board,
    delete_session,
    get_board,
    get_database_path,
    initialize_database,
    list_boards,
    list_user_sessions,
    reorder_boards,
    resolve_session,
    update_board_data,
    update_board_meta,
    update_user_profile,
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

DeepSeekCheckResult = Union[dict[str, str], Awaitable[dict[str, str]]]
DeepSeekCheckFn = Callable[[], DeepSeekCheckResult]
AICompletionResult = Union[str, Awaitable[str]]
AICompletionFn = Callable[[list[dict[str, str]]], AICompletionResult]

# Map storage exceptions to HTTP status codes. Order matters: subclasses first.
_STORAGE_STATUS = (
    (NotFoundError, 404),
    (ConflictError, 409),
    (AuthError, 401),
    (StorageError, 400),
)


def _http_from_storage(error: StorageError) -> HTTPException:
    for exc_type, code in _STORAGE_STATUS:
        if isinstance(error, exc_type):
            return HTTPException(status_code=code, detail=str(error))
    return HTTPException(status_code=400, detail=str(error))


# ---------------- Pydantic schemas -----------------------------------------


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str
    displayName: str | None = None


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    displayName: str | None = None


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currentPassword: str
    newPassword: str


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
    priority: str | None = None
    dueDate: str | None = None
    labels: list[str] = Field(default_factory=list)
    assignee: str | None = None


class BoardColumnPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    cardIds: list[str]


class BoardDataPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    columns: list[BoardColumnPayload]
    cards: dict[str, BoardCardPayload]


class CreateBoardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    data: BoardDataPayload | None = None


class UpdateBoardMetaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None


class UpdateBoardDataRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: BoardDataPayload
    expectedUpdatedAt: str | None = None


class ReorderBoardsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boardIds: list[int]


# ---------------- Helpers ---------------------------------------------------


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def create_app(
    static_dir: Path = STATIC_DIR,
    database_path: Path | None = None,
    deepseek_check: DeepSeekCheckFn | None = None,
    ai_completion: AICompletionFn | None = None,
) -> FastAPI:
    app = FastAPI(title="Project Management App")
    db_path = database_path or get_database_path()
    initialize_database(db_path)
    deepseek_check_fn = deepseek_check or run_connectivity_check

    if static_dir.exists():
        app.mount(
            "/_next",
            StaticFiles(directory=static_dir / "_next", check_dir=False),
            name="next-static",
        )

    def current_user(
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        token = _bearer_token(authorization)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            return resolve_session(db_path, token)
        except AuthError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
                headers={"WWW-Authenticate": "Bearer"},
            ) from error

    def current_token(
        authorization: str | None = Header(default=None),
    ) -> str:
        token = _bearer_token(authorization)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token

    # ------------- Static / health ----------------------------------------

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html", media_type="text/html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(static_dir / "favicon.ico")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # ------------- Auth ----------------------------------------------------

    @app.post("/api/auth/signup", status_code=201)
    def signup(payload: SignupRequest = Body(...)) -> dict[str, Any]:
        try:
            user = create_user(
                db_path,
                payload.username,
                payload.password,
                payload.displayName,
            )
            session = create_session(db_path, user["id"])
        except StorageError as error:
            raise _http_from_storage(error) from error
        return {"user": user, "session": session}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest = Body(...)) -> dict[str, Any]:
        try:
            user = authenticate(db_path, payload.username, payload.password)
            session = create_session(db_path, user["id"])
        except StorageError as error:
            raise _http_from_storage(error) from error
        return {"user": user, "session": session}

    @app.post("/api/auth/logout")
    def logout(token: str = Depends(current_token)) -> dict[str, bool]:
        deleted = delete_session(db_path, token)
        return {"loggedOut": deleted}

    @app.get("/api/auth/me")
    def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        return user

    @app.put("/api/auth/profile")
    def update_profile(
        payload: ProfileUpdateRequest = Body(...),
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        try:
            return update_user_profile(db_path, user["id"], payload.displayName)
        except StorageError as error:
            raise _http_from_storage(error) from error

    @app.put("/api/auth/password")
    def change_user_password(
        payload: PasswordChangeRequest = Body(...),
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, bool]:
        try:
            change_password(
                db_path,
                user["id"],
                payload.currentPassword,
                payload.newPassword,
            )
        except StorageError as error:
            raise _http_from_storage(error) from error
        return {"changed": True}

    @app.get("/api/auth/sessions")
    def get_user_sessions(
        user: dict[str, Any] = Depends(current_user),
    ) -> list[dict[str, Any]]:
        return list_user_sessions(db_path, user["id"])

    # ------------- Boards --------------------------------------------------

    @app.get("/api/boards")
    def get_boards(
        user: dict[str, Any] = Depends(current_user),
    ) -> list[dict[str, Any]]:
        return list_boards(db_path, user["id"])

    @app.post("/api/boards", status_code=201)
    def post_board(
        payload: CreateBoardRequest = Body(...),
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        try:
            data = payload.data.model_dump() if payload.data else None
            return create_board(
                db_path, user["id"], payload.title, payload.description, data
            )
        except StorageError as error:
            raise _http_from_storage(error) from error

    @app.put("/api/boards/order")
    def reorder_user_boards(
        payload: ReorderBoardsRequest = Body(...),
        user: dict[str, Any] = Depends(current_user),
    ) -> list[dict[str, Any]]:
        try:
            return reorder_boards(db_path, user["id"], payload.boardIds)
        except StorageError as error:
            raise _http_from_storage(error) from error

    @app.get("/api/boards/{board_id}")
    def get_one_board(
        board_id: int,
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        try:
            return get_board(db_path, user["id"], board_id)
        except StorageError as error:
            raise _http_from_storage(error) from error

    @app.patch("/api/boards/{board_id}")
    def patch_board_meta(
        board_id: int,
        payload: UpdateBoardMetaRequest = Body(...),
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        try:
            return update_board_meta(
                db_path, user["id"], board_id, payload.title, payload.description
            )
        except StorageError as error:
            raise _http_from_storage(error) from error

    @app.put("/api/boards/{board_id}/data")
    def put_board_data(
        board_id: int,
        payload: UpdateBoardDataRequest = Body(...),
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        try:
            return update_board_data(
                db_path,
                user["id"],
                board_id,
                payload.data.model_dump(),
                payload.expectedUpdatedAt,
            )
        except StorageError as error:
            raise _http_from_storage(error) from error

    @app.delete("/api/boards/{board_id}", status_code=204)
    def delete_one_board(
        board_id: int,
        user: dict[str, Any] = Depends(current_user),
    ) -> None:
        try:
            delete_board(db_path, user["id"], board_id)
        except StorageError as error:
            raise _http_from_storage(error) from error

    # ------------- AI chat (board-scoped) ---------------------------------

    @app.post("/api/boards/{board_id}/ai/chat")
    async def ai_chat(
        board_id: int,
        payload: AiChatRequest = Body(...),
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        try:
            user_message = validate_user_message(payload.message)
            history = validate_history(
                [item.model_dump() for item in payload.history]
            )
            current_board = get_board(db_path, user["id"], board_id)
            ai_response = await ask_ai_for_board_update(
                current_board["data"], user_message, history, ai_completion
            )
            updated_board_data = ai_response["board"]
            board_after = current_board
            if updated_board_data is not None:
                # Optimistic concurrency guard: ensure the board hasn't moved
                # underneath us while the AI was responding.
                latest = get_board(db_path, user["id"], board_id)
                if latest["data"] != current_board["data"]:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Board changed while the AI was responding. "
                            "Please retry the request."
                        ),
                    )
                board_after = update_board_data(
                    db_path, user["id"], board_id, updated_board_data
                )

            next_history = [
                *history,
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": ai_response["assistantMessage"]},
            ]
            return {
                "assistantMessage": ai_response["assistantMessage"],
                "board": board_after if updated_board_data is not None else None,
                "operationSummary": ai_response["operationSummary"],
                "history": next_history,
            }
        except AIResponseError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except StorageError as error:
            raise _http_from_storage(error) from error
        except ValueError as error:
            # Bare ValueError from message/history validation in app.ai.
            raise HTTPException(status_code=400, detail=str(error)) from error
        except DeepSeekConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except DeepSeekAPIError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    # ------------- DeepSeek connectivity check -----------------------------

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
