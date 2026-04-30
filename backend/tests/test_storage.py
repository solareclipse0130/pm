import copy

import pytest

from app.storage import (
    MAX_CARDS,
    MAX_COLUMNS,
    MAX_DETAILS_LENGTH,
    MAX_ID_LENGTH,
    MAX_TITLE_LENGTH,
    create_default_board,
    validate_board,
)


def make_valid_board() -> dict:
    return create_default_board("2026-01-01T00:00:00Z")


def test_validate_board_accepts_default_board() -> None:
    validate_board(make_valid_board())


@pytest.mark.parametrize(
    "board, message",
    [
        (None, "Board must be an object."),
        ([], "Board must be an object."),
        ({}, "Board version must be 1."),
        ({"version": 2, "columns": [], "cards": {}}, "Board version must be 1."),
    ],
)
def test_validate_board_rejects_top_level_shape(board, message) -> None:
    with pytest.raises(ValueError, match=message):
        validate_board(board)


def test_validate_board_rejects_empty_columns() -> None:
    board = make_valid_board()
    board["columns"] = []
    with pytest.raises(ValueError, match="at least one column"):
        validate_board(board)


def test_validate_board_rejects_non_dict_columns_entry() -> None:
    board = make_valid_board()
    board["columns"][0] = "not-a-dict"
    with pytest.raises(ValueError, match="must be an object"):
        validate_board(board)


def test_validate_board_rejects_duplicate_column_ids() -> None:
    board = make_valid_board()
    board["columns"][1]["id"] = board["columns"][0]["id"]
    with pytest.raises(ValueError, match="Column ids must be unique"):
        validate_board(board)


def test_validate_board_rejects_missing_column_id() -> None:
    board = make_valid_board()
    board["columns"][0]["id"] = ""
    with pytest.raises(ValueError, match="Each column must have an id"):
        validate_board(board)


def test_validate_board_rejects_non_string_card_ids() -> None:
    board = make_valid_board()
    board["columns"][0]["cardIds"] = [123]
    with pytest.raises(ValueError, match="cardIds as strings"):
        validate_board(board)


def test_validate_board_rejects_card_in_two_columns() -> None:
    board = make_valid_board()
    duplicated_id = board["columns"][0]["cardIds"][0]
    board["columns"][1]["cardIds"].append(duplicated_id)
    with pytest.raises(ValueError, match="only one column"):
        validate_board(board)


def test_validate_board_rejects_missing_card_reference() -> None:
    board = make_valid_board()
    board["columns"][0]["cardIds"].append("missing-card")
    with pytest.raises(ValueError, match="must refer to an existing card"):
        validate_board(board)


def test_validate_board_rejects_orphan_card() -> None:
    board = make_valid_board()
    board["cards"]["orphan"] = {
        "id": "orphan",
        "title": "Orphan",
        "details": "",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }
    with pytest.raises(ValueError, match="must be assigned to a column"):
        validate_board(board)


def test_validate_board_rejects_card_id_mismatch() -> None:
    board = make_valid_board()
    board["cards"]["card-1"]["id"] = "card-99"
    with pytest.raises(ValueError, match="Card keys must match"):
        validate_board(board)


def test_validate_board_rejects_card_missing_details() -> None:
    board = make_valid_board()
    board["cards"]["card-1"].pop("details")
    with pytest.raises(ValueError, match="must have details"):
        validate_board(board)


def test_validate_board_rejects_too_many_columns() -> None:
    board = make_valid_board()
    template = copy.deepcopy(board["columns"][0])
    extra_columns = []
    for index in range(MAX_COLUMNS):
        column = copy.deepcopy(template)
        column["id"] = f"extra-col-{index}"
        column["cardIds"] = []
        extra_columns.append(column)
    board["columns"].extend(extra_columns)
    with pytest.raises(ValueError, match=f"at most {MAX_COLUMNS} columns"):
        validate_board(board)


def test_validate_board_rejects_too_long_title() -> None:
    board = make_valid_board()
    board["columns"][0]["title"] = "x" * (MAX_TITLE_LENGTH + 1)
    with pytest.raises(ValueError, match="Column title must be"):
        validate_board(board)


def test_validate_board_rejects_too_long_card_details() -> None:
    board = make_valid_board()
    board["cards"]["card-1"]["details"] = "x" * (MAX_DETAILS_LENGTH + 1)
    with pytest.raises(ValueError, match="Card details must be"):
        validate_board(board)


def test_validate_board_rejects_too_long_card_id() -> None:
    board = make_valid_board()
    long_id = "x" * (MAX_ID_LENGTH + 1)
    board["cards"][long_id] = {
        "id": long_id,
        "title": "Long",
        "details": "",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }
    board["columns"][0]["cardIds"].append(long_id)
    with pytest.raises(ValueError, match="Card id must be"):
        validate_board(board)


def test_validate_board_rejects_too_many_cards() -> None:
    board = make_valid_board()
    board["columns"][0]["cardIds"] = []
    board["columns"][1]["cardIds"] = []
    board["columns"][2]["cardIds"] = []
    board["columns"][3]["cardIds"] = []
    board["columns"][4]["cardIds"] = []
    board["cards"] = {}
    target = MAX_CARDS + 1
    extra_card_ids = []
    for index in range(target):
        card_id = f"bulk-{index}"
        board["cards"][card_id] = {
            "id": card_id,
            "title": "Bulk",
            "details": "",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
        extra_card_ids.append(card_id)
    board["columns"][0]["cardIds"] = extra_card_ids
    with pytest.raises(ValueError, match=f"at most {MAX_CARDS} cards"):
        validate_board(board)
