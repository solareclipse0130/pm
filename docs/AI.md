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

## Reliability Boundaries

The AI path is intentionally small, but it has a few guardrails:

- The backend sends the current board JSON as the source of truth for each request.
- Chat history is bounded to the most recent 12 messages, and each history item is capped at 2000 characters.
- User messages are capped at 2000 characters.
- DeepSeek must return exactly `assistantMessage`, `board`, and `operationSummary`.
- Any returned board is validated before it is saved.
- If the persisted board changes while the AI request is in progress, the backend returns `409` and does not save the AI update.
- AI and DeepSeek errors are returned as API errors; the frontend shows the backend detail when available.

These checks reduce accidental board corruption while keeping the MVP simple. The AI still remains a best-effort assistant, so production use would need stronger auth, audit logs, and operation-level conflict handling.
