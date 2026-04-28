import json

import pytest

from app.ai import (
    AIResponseError,
    ask_ai_for_board_update,
    build_ai_messages,
    parse_ai_response,
    validate_history,
    validate_user_message,
)
from app.storage import create_default_board


def test_validate_user_message_trims_text() -> None:
    assert validate_user_message("  move this card  ") == "move this card"


def test_validate_user_message_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="Message"):
        validate_user_message("   ")


def test_validate_user_message_rejects_oversized_text() -> None:
    with pytest.raises(ValueError, match="2000"):
        validate_user_message("x" * 2001)


def test_validate_history_accepts_user_and_assistant_messages() -> None:
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]

    assert validate_history(history) == history


def test_validate_history_keeps_recent_bounded_context() -> None:
    history = [
        {"role": "user", "content": f"message-{index}"}
        for index in range(14)
    ]

    validated = validate_history(history)

    assert len(validated) == 12
    assert validated[0]["content"] == "message-2"
    assert validated[-1]["content"] == "message-13"


def test_validate_history_trims_long_content() -> None:
    validated = validate_history([{"role": "user", "content": "x" * 2001}])

    assert len(validated[0]["content"]) == 2000


def test_validate_history_rejects_unknown_roles() -> None:
    with pytest.raises(ValueError, match="History role"):
        validate_history([{"role": "system", "content": "No"}])


def test_build_ai_messages_includes_board_history_and_user_message() -> None:
    board = create_default_board("2026-01-01T00:00:00Z")
    history = [{"role": "assistant", "content": "Ready."}]

    messages = build_ai_messages(board, "Add a card", history)

    assert messages[0]["role"] == "system"
    assert "assistantMessage" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "Current Kanban board JSON" in messages[1]["content"]
    assert '"columns"' in messages[1]["content"]
    assert messages[2] == {"role": "assistant", "content": "Ready."}
    assert messages[3] == {"role": "user", "content": "Add a card"}


def test_parse_ai_response_accepts_no_update_reply() -> None:
    response = parse_ai_response(
        json.dumps(
            {
                "assistantMessage": "No board changes needed.",
                "board": None,
                "operationSummary": None,
            }
        )
    )

    assert response == {
        "assistantMessage": "No board changes needed.",
        "board": None,
        "operationSummary": None,
    }


def test_parse_ai_response_accepts_card_edit_update() -> None:
    board = create_default_board("2026-01-01T00:00:00Z")
    board["cards"]["card-1"]["title"] = "Updated by AI"

    response = parse_ai_response(
        json.dumps(
            {
                "assistantMessage": "Updated the card.",
                "board": board,
                "operationSummary": "Renamed card-1.",
            }
        )
    )

    assert response["board"]["cards"]["card-1"]["title"] == "Updated by AI"


def test_parse_ai_response_accepts_card_creation_update() -> None:
    board = create_default_board("2026-01-01T00:00:00Z")
    board["cards"]["card-9"] = {
        "id": "card-9",
        "title": "New AI card",
        "details": "Created through structured output.",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }
    board["columns"][0]["cardIds"].append("card-9")

    response = parse_ai_response(
        json.dumps(
            {
                "assistantMessage": "Created the card.",
                "board": board,
                "operationSummary": "Added card-9.",
            }
        )
    )

    assert response["board"]["cards"]["card-9"]["title"] == "New AI card"
    assert "card-9" in response["board"]["columns"][0]["cardIds"]


def test_parse_ai_response_accepts_card_move_update() -> None:
    board = create_default_board("2026-01-01T00:00:00Z")
    board["columns"][0]["cardIds"].remove("card-1")
    board["columns"][-1]["cardIds"].append("card-1")

    response = parse_ai_response(
        json.dumps(
            {
                "assistantMessage": "Moved the card.",
                "board": board,
                "operationSummary": "Moved card-1 to Done.",
            }
        )
    )

    assert "card-1" not in response["board"]["columns"][0]["cardIds"]
    assert "card-1" in response["board"]["columns"][-1]["cardIds"]


def test_parse_ai_response_rejects_invalid_json() -> None:
    with pytest.raises(AIResponseError, match="valid JSON"):
        parse_ai_response("not json")


def test_parse_ai_response_rejects_extra_or_missing_keys() -> None:
    with pytest.raises(AIResponseError, match="assistantMessage, board"):
        parse_ai_response(
            json.dumps(
                {
                    "assistantMessage": "Updated.",
                    "board": None,
                    "operationSummary": None,
                    "extra": "not allowed",
                }
            )
        )


def test_parse_ai_response_rejects_invalid_board_update() -> None:
    board = create_default_board("2026-01-01T00:00:00Z")
    board["columns"][0]["cardIds"].append("missing-card")

    with pytest.raises(AIResponseError, match="AI board update is invalid"):
        parse_ai_response(
            json.dumps(
                {
                    "assistantMessage": "I changed it.",
                    "board": board,
                    "operationSummary": None,
                }
            )
        )


def test_ask_ai_for_board_update_uses_mocked_completion() -> None:
    board = create_default_board("2026-01-01T00:00:00Z")
    captured: dict[str, object] = {}

    def fake_completion(messages: list[dict[str, str]]) -> str:
        captured["messages"] = messages
        return json.dumps(
            {
                "assistantMessage": "Created the card.",
                "board": board,
                "operationSummary": "Added a backlog card.",
            }
        )

    response = ask_ai_for_board_update(
        board,
        "Create a backlog card",
        [],
        fake_completion,
    )

    assert response["assistantMessage"] == "Created the card."
    assert response["board"] == board
    assert captured["messages"]
