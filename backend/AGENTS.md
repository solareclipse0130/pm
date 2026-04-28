# Backend

This directory contains the FastAPI backend for the Project Management MVP.

## Structure

- `app/main.py` defines the FastAPI app.
- `app/deepseek.py` contains the DeepSeek API client and connectivity check.
- `app/storage.py` contains SQLite persistence and Kanban board validation.
- `static/` holds the static site served at `/`; Docker replaces it with the built NextJS export.
- `tests/` contains backend tests.
- `pyproject.toml` defines Python dependencies and pytest settings.

## Commands

From `backend/`:

- Install dependencies with uv: `uv sync --extra dev`
- Run tests: `uv run --extra dev pytest`
- Run locally: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Check DeepSeek connectivity locally: `curl http://localhost:8000/api/dev/deepseek-check`

If `uv` is not installed locally, use a temporary Python virtual environment for local testing. Docker must still use `uv`.

## Conventions

- Keep routes small and explicit.
- Keep API responses predictable.
- Do not log secrets.
- Prefer simple functions over extra layers until the MVP needs them.
