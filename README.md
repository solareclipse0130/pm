# Project Management MVP

Local-only Kanban app with an AI chat sidebar. NextJS frontend (statically
exported), FastAPI backend, SQLite persistence, single Docker container.

## Run

See [docs/RUNNING.md](docs/RUNNING.md) for the platform-specific Docker scripts
and environment setup.

## Project layout

- `backend/` — FastAPI app (`app/main.py`, `app/storage.py`, `app/ai.py`,
  `app/deepseek.py`) and pytest suite.
- `frontend/` — NextJS app, built into static files served by the backend.
- `scripts/` — start/stop scripts for Linux, macOS, and Windows.
- `docs/` — runtime, schema, AI, auth, and acceptance documentation.
- `strategy/` — long-term product evolution and iteration workflow.

For full project context and binding constraints see `AGENTS.md`.
