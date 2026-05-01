# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local-only Project Management MVP: a NextJS Kanban frontend statically exported and served by a FastAPI backend, with a DeepSeek-powered AI chat sidebar that can create/edit/move cards. Everything runs in a single Docker container with SQLite persistence.

Authoritative product scope and constraints live in the root `AGENTS.md`. Phase-by-phase task history lives in `docs/PLAN.md` (all phases are complete; treat it as a record, not a TODO list).

## Common Commands

### Backend (`backend/`)
- Install: `uv sync --extra dev`
- Run tests: `uv run --extra dev pytest`
- Run single test: `uv run --extra dev pytest tests/test_ai.py::test_name`
- Run locally: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
- DeepSeek connectivity check: `curl http://localhost:8000/api/dev/deepseek-check`

### Frontend (`frontend/`)
- Install: `npm install`
- Dev: `npm run dev`
- Static export build: `npm run build` (outputs to `frontend/out/`, copied into the backend image as `static/`)
- Lint: `npm run lint`
- Unit tests (Vitest): `npm run test:unit`
- Single unit test: `npx vitest run path/to/file.test.tsx -t "test name"`
- E2E tests (Playwright): `npm run test:e2e`

### Full app (Docker)
- Start: `./scripts/start-linux.sh` (or `start-mac.sh` / `start-windows.ps1`)
- Stop: corresponding `stop-*` script
- Default URL: `http://localhost:9000` (override with `PORT=9010 ./scripts/start-linux.sh`)
- Image and container name: `pm-mvp`. Container listens on `8000`; the start scripts publish `host:9000 -> container:8000` and bind-mount project `data/` to `/app/data` so `app.db` survives rebuilds.

## Architecture

### Single-container topology
The Dockerfile is two-stage: stage 1 (`node:24`) runs `next build` to produce `frontend/out/`; stage 2 (`python:3.14-slim`) installs backend deps with `uv` and copies the built frontend into `backend/static/`. FastAPI then serves `index.html` at `/` and Next's chunks at `/_next` via `StaticFiles`. There is no separate Node server at runtime — keep the frontend a pure static export (`output: 'export'`) and avoid server-only NextJS features.

### Backend (`backend/app/`)
Four modules, intentionally flat:
- `main.py` — `create_app()` factory wires routes and accepts injectable `database_path`, `deepseek_check`, and `ai_completion` for tests. The module-level `app = create_app()` is what uvicorn loads.
- `storage.py` — SQLite init, the `users`/`boards` schema (board stored as JSON in `boards.data`), default-board creation for the MVP user, and board-shape validation. Schema and validation rules are documented in `docs/DATABASE.md` — keep them in sync.
- `ai.py` — Prompt construction, structured-response parsing, and validation of the AI's `{assistantMessage, board, operationSummary}` payload. Caps history to 12 messages and 2000 chars per message; user messages also capped at 2000 chars.
- `deepseek.py` — Thin DeepSeek HTTP client, reads `DEEPSEEK_API_KEY` from project root `.env` or the process env. Raises `DeepSeekConfigurationError` (missing key → 400) vs `DeepSeekAPIError` (upstream failure → 502).

Key request flow for `POST /api/ai/chat`: load current board → call DeepSeek → validate response → re-read board and **reject with 409 if it changed mid-flight** → save. This optimistic check is the only conflict-handling in the MVP; do not weaken it.

### Frontend (`frontend/src/`)
- `app/page.tsx` — Top-level entry; gates on the local sign-in.
- `components/AppShell.tsx` — Layout, login gate, board state, chat sidebar wiring.
- `components/Kanban*.tsx` — DnD-kit board, columns, cards.
- `components/AiChatSidebar.tsx` — Chat UI; on each AI reply that includes a `board`, replaces the visible board.
- `lib/kanban.ts` — Board shape, default board (column/card ids must match the backend default in `storage.py`), and movement helpers.
- `lib/boardApi.ts` / `lib/aiApi.ts` — Fetch wrappers for `/api/board` and `/api/ai/chat`.

### Auth boundary (important)
Login is hardcoded `user` / `password` on the frontend only. The backend uses a fixed MVP username `user` for persistence and **does not enforce any session/token on API routes**. See `docs/AUTH.md`. Do not pretend this is real auth; if you add features that imply multi-user isolation, flag the gap rather than silently relying on the boundary.

## Conventions

From root `AGENTS.md` (binding):
- No emojis, anywhere — code, docs, commits, UI.
- Keep it simple. No defensive programming for impossible cases, no speculative abstractions, no extra MVP features.
- Root-cause first: when something breaks, prove the cause with evidence before changing code. Don't guess-fix.
- Confirm current package versions from official sources before adding/upgrading deps.
- Preserve user changes already in the worktree.
- Color scheme — "Coastal Calm" (use these exact hex values for any new UI):
  - Deep Sea `#0F2A47` (text/deep surfaces), Pacific Blue `#0085A1` (primary/CTA), Aqua Mist `#7BC4BC` (secondary highlight), Coral Sunset `#F2715E` (complementary accent/warnings), Sand Dune `#F4E1C1` (warm neutral), Slate `#6B7A8F` (supporting text), Foam `#EAF3F4` (page background).
  - CSS variable names in `frontend/src/app/globals.css`: `--deep-sea`, `--pacific-blue`, `--aqua-mist`, `--coral-sunset`, `--sand-dune`, `--slate`, `--foam`.

Backend specifics: keep routes small and explicit, responses predictable, no secret logging, prefer plain functions over layers.

Frontend specifics: keep the static-export constraint, preserve existing drag/edit/add/delete behavior unless a task explicitly changes it.

## Environment

- `DEEPSEEK_API_KEY` — required for real AI calls; loaded from project root `.env` or process env. Tests mock the client and don't need it.
- `DATABASE_PATH` — overrides the SQLite path (defaults to `./data/app.db` locally, `/app/data/app.db` in Docker).
- `PORT` — host port for the start scripts (default `9000`).
