# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local-only Project Management app: a NextJS Kanban frontend statically exported and served by a FastAPI backend, with a DeepSeek-powered AI chat sidebar that can create/edit/move cards. Everything runs in a single Docker container with SQLite persistence.

The app supports real multi-user accounts (signup/login with hashed passwords + bearer-token sessions) and multiple boards per user. The legacy MVP credentials `user` / `password` are still seeded on first init for convenience.

Authoritative product scope and constraints live in the root `AGENTS.md`. Phase-by-phase task history lives in `docs/PLAN.md` (treat it as a historical record, not a TODO list).

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
- `storage.py` — SQLite init, schema (users/sessions/boards), password hashing (scrypt), session token issuance/resolution, board CRUD with optimistic concurrency, and board-JSON validation. Storage helpers raise `StorageError` / `AuthError` / `NotFoundError` / `ConflictError` (all subclasses of `ValueError`).
- `ai.py` — Prompt construction, structured-response parsing, and validation of the AI's `{assistantMessage, board, operationSummary}` payload. Caps history to 12 messages and 2000 chars per message; user messages also capped at 2000 chars.
- `deepseek.py` — Thin DeepSeek HTTP client, reads `DEEPSEEK_API_KEY` from project root `.env` or the process env. Raises `DeepSeekConfigurationError` vs `DeepSeekAPIError`.

API surface (all `/api/...`):
- Auth: `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `PUT /auth/profile`, `PUT /auth/password`, `GET /auth/sessions`. Authenticated endpoints expect `Authorization: Bearer <token>`.
- Boards: `GET /boards`, `POST /boards`, `GET /boards/{id}`, `PATCH /boards/{id}` (title/description), `PUT /boards/{id}/data` (full board JSON), `DELETE /boards/{id}`, `PUT /boards/order` (reorder).
- AI chat: `POST /boards/{id}/ai/chat`. Same optimistic-concurrency guard as before — load current board, call DeepSeek, re-read, **409 if board changed mid-flight**, then save. Do not weaken this.

Card JSON (in `boards.data`) supports optional fields: `priority` (`low`/`medium`/`high`/`urgent` or null), `dueDate` (`YYYY-MM-DD` or null), `labels` (string array, ≤10 entries, ≤40 chars each), `assignee` (username string or null). `storage.normalize_board` fills missing fields with safe defaults so legacy payloads still validate.

Schema migrations: `PRAGMA user_version` tracks schema; `_migrate_legacy_v0` rebuilds the legacy single-board-per-user `boards` table when an older DB is found. Tests in `tests/test_boards.py::test_initialize_database_migrates_legacy_single_board_schema` exercise the path.

### Frontend (`frontend/src/`)
- `app/page.tsx` — Top-level entry.
- `components/AppShell.tsx` — Login + signup form, session restore, hands off to `Workspace` when authenticated.
- `components/Workspace.tsx` — Loads boards list, manages selected board id (persisted in `localStorage`), wires `BoardSwitcher` and `KanbanBoard`.
- `components/BoardSwitcher.tsx` — Sidebar with create/rename/delete/select per board.
- `components/Kanban*.tsx` — DnD-kit board/columns/cards. `KanbanBoard` now takes a `board: BoardDetail` prop and an `onBoardChanged` callback (no internal fetch).
- `components/AiChatSidebar.tsx` — Chat UI; per-board, scoped via `KanbanBoard`.
- `lib/authClient.ts` — `login`/`signup`/`logout`/`fetchCurrentUser`/`apiFetch`; persists session token in `localStorage` under `pm-session-v1` and injects `Authorization` header on every `apiFetch`.
- `lib/boardApi.ts` — list/get/create/update/delete/reorder for boards.
- `lib/aiApi.ts` — `sendAiMessage(boardId, message, history)`.
- `lib/kanban.ts` — Board/Card types (with priority/labels/dueDate/assignee extensions), `moveCard`, id/timestamp helpers.

### Auth boundary
Real authentication: passwords stored as `scrypt$N$r$p$salt$hash`, sessions are random `secrets.token_urlsafe(32)` strings with 30-day TTL kept in the `sessions` table. Backend dependencies enforce `Authorization: Bearer <token>` on every authenticated route and 401 on missing/expired tokens. The MVP user (`user`/`password`) is still auto-seeded for convenience. `docs/AUTH.md` is out of date — believe the code.

## Conventions

From root `AGENTS.md` (binding):
- No emojis, anywhere — code, docs, commits, UI.
- Keep it simple. No defensive programming for impossible cases, no speculative abstractions, no extra MVP features.
- Root-cause first: when something breaks, prove the cause with evidence before changing code. Don't guess-fix.
- Confirm current package versions from official sources before adding/upgrading deps.
- Preserve user changes already in the worktree.
- Color scheme — "Harbor & Ember" (low-saturation Pantone blues + brick red; use these exact hex values for any new UI):
  - Deep Sea `#1F3055` (text/deep surfaces, Pantone 19-3919 Insignia Blue), Pacific Blue `#487090` (primary/CTA, Pantone 18-4032 Riverside), Aqua Mist `#84A0B0` (secondary highlight, Pantone 14-4214 Stone Blue), Coral Sunset `#B5544A` (red emphasis/warnings, Pantone 18-1547 Aurora Red), Sand Dune `#EDE0CC` (warm neutral, Pantone 13-1010 Vanilla Cream), Slate `#888B8D` (supporting text, Pantone 16-3915 Alloy), Foam `#E2E8E5` (page background, Pantone 12-4302 Glacier Lake).
  - CSS variable names in `frontend/src/app/globals.css`: `--deep-sea`, `--pacific-blue`, `--aqua-mist`, `--coral-sunset`, `--sand-dune`, `--slate`, `--foam` (kept from the prior "Coastal Calm" palette so class names continue to work).

Backend specifics: keep routes small and explicit, responses predictable, no secret logging, prefer plain functions over layers.

Frontend specifics: keep the static-export constraint, preserve existing drag/edit/add/delete behavior unless a task explicitly changes it.

## Environment

- `DEEPSEEK_API_KEY` — required for real AI calls; loaded from project root `.env` or process env. Tests mock the client and don't need it.
- `DATABASE_PATH` — overrides the SQLite path (defaults to `./data/app.db` locally, `/app/data/app.db` in Docker).
- `PORT` — host port for the start scripts (default `9000`).
