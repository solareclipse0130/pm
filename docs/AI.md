# AI Backend

The backend sends the current Kanban board, the user's message, and optional chat history to DeepSeek.

## Endpoint

`POST /api/ai/chat`

Request:

```json
{
  "message": "Create a card for launch notes",
  "history": [
    { "role": "user", "content": "Previous question" },
    { "role": "assistant", "content": "Previous answer" }
  ]
}
```

Response:

```json
{
  "assistantMessage": "Created the card.",
  "board": null,
  "operationSummary": null,
  "history": []
}
```

## Structured AI Response

DeepSeek must return JSON with:

- `assistantMessage`: user-facing reply.
- `board`: full updated Kanban board JSON, or `null` when no board change is needed.
- `operationSummary`: short summary, or `null`.

The backend validates any returned board before saving. Invalid AI output returns an error and leaves the persisted board unchanged.

Conversation history is returned to the caller for the MVP. It is not stored in SQLite.

The frontend chat sidebar sends messages to this endpoint and replaces the visible Kanban board when the response includes a board update.
