# Database Approach

The MVP uses one local SQLite database. The backend creates it automatically if it does not exist.

The app keeps the schema small: users are relational rows, and each user's single board is stored as JSON. This supports the MVP without splitting Kanban cards and columns into many tables too early.

## Tables

```sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
```

## MVP User

Phase 6 should create the MVP user if it does not exist:

```text
username: user
```

The password remains hardcoded in the frontend for Phase 4. The database does not store a password in the MVP.

If real authentication is added later, add a password field or a separate credentials table in a later migration.

## Board JSON

`boards.data` stores UTF-8 JSON with this shape:

```json
{
  "version": 1,
  "columns": [
    {
      "id": "col-backlog",
      "title": "Backlog",
      "cardIds": ["card-1", "card-2"]
    }
  ],
  "cards": {
    "card-1": {
      "id": "card-1",
      "title": "Align roadmap themes",
      "details": "Draft quarterly themes with impact statements and metrics.",
      "createdAt": "2026-01-01T00:00:00Z",
      "updatedAt": "2026-01-01T00:00:00Z"
    }
  }
}
```

Column order is the order of the `columns` array.

Card order is the order of each column's `cardIds` array.

The `cards` object stores card details by id so moving a card only changes column `cardIds`.

## Default Board

When the MVP user has no board, Phase 6 should create one from the current frontend default Kanban data.

Default creation should be deterministic:

- Use the same column ids and card ids as `frontend/src/lib/kanban.ts`.
- Add `version: 1`.
- Add `createdAt` and `updatedAt` to each card.
- Use the current UTC time for timestamps when the default board is first inserted.

## Validation

Phase 6 should reject board JSON unless all rules below pass:

- `version` must be `1`.
- `columns` must be a non-empty array.
- Every column must have a non-empty string `id`.
- Every column must have a string `title`.
- Every column must have a `cardIds` array of strings.
- Column ids must be unique.
- `cards` must be an object keyed by card id.
- Every card key must match the card's `id`.
- Every card must have string `title` and string `details`.
- Every `cardIds` entry must refer to an existing card.
- A card id may appear in only one column.
- The board may contain cards that are not currently in a column only if a later phase explicitly needs archived cards. For now, reject them.

Keep validation simple and return a clear 400 response when validation fails.

## Why This Supports The MVP

The MVP has one hardcoded signed-in user and one board per signed-in user. The `users.username` unique constraint and `boards.user_id` unique constraint directly model that.

The schema can support multiple users later by inserting more `users` rows. Each user can still have exactly one board because `boards.user_id` is unique.

If the app later needs multiple boards per user, remove the unique constraint on `boards.user_id` and add a board name column in a migration.
