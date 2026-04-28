from __future__ import annotations

import json
from typing import Any, Callable

from app.deepseek import create_chat_completion
from app.storage import validate_board

CompletionFn = Callable[[list[dict[str, str]]], str]

SYSTEM_PROMPT = """You help manage a Kanban board for a project management app.
Return only valid JSON with this exact shape:
{
  "assistantMessage": "short user-facing response",
  "board": null,
  "operationSummary": null
}
Set "board" to a full updated Kanban board JSON object only when the user asks
for a card or column change. Otherwise leave "board" as null. Preserve the
existing board schema exactly. Do not invent extra top-level keys."""


class AIResponseError(ValueError):
    pass


def validate_history(history: Any) -> list[dict[str, str]]:
    if history is None:
        return []
    if not isinstance(history, list):
        raise ValueError("History must be a list.")

    validated: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            raise ValueError("Each history item must be an object.")
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"}:
            raise ValueError("History role must be user or assistant.")
        if not isinstance(content, str):
            raise ValueError("History content must be a string.")
        validated.append({"role": role, "content": content})
    return validated


def validate_user_message(message: Any) -> str:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message must be a non-empty string.")
    return message.strip()


def build_ai_messages(
    board: dict[str, Any],
    user_message: str,
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    board_json = json.dumps(board, ensure_ascii=False, separators=(",", ":"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Current Kanban board JSON:\n"
                f"{board_json}\n\nUse this board as the source of truth."
            ),
        },
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


def parse_ai_response(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as error:
        raise AIResponseError("AI response was not valid JSON.") from error

    if not isinstance(parsed, dict):
        raise AIResponseError("AI response must be an object.")

    assistant_message = parsed.get("assistantMessage")
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        raise AIResponseError("AI response must include assistantMessage.")

    board = parsed.get("board")
    if board is not None:
        try:
            validate_board(board)
        except ValueError as error:
            raise AIResponseError(f"AI board update is invalid: {error}") from error

    operation_summary = parsed.get("operationSummary")
    if operation_summary is not None and not isinstance(operation_summary, str):
        raise AIResponseError("AI operationSummary must be a string or null.")

    return {
        "assistantMessage": assistant_message.strip(),
        "board": board,
        "operationSummary": operation_summary,
    }


def ask_ai_for_board_update(
    board: dict[str, Any],
    user_message: str,
    history: list[dict[str, str]],
    completion_fn: CompletionFn | None = None,
) -> dict[str, Any]:
    messages = build_ai_messages(board, user_message, history)
    if completion_fn:
        content = completion_fn(messages)
    else:
        content = create_chat_completion(
            messages,
            response_format={"type": "json_object"},
        )
    return parse_ai_response(content)
