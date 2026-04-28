# Project Plan

This plan breaks the Project Management MVP into reviewable phases. Each phase should be completed, tested, and summarized before moving to the next phase. Do not add extra product features beyond the MVP described in `AGENTS.md`.

## Current Decisions

- Frontend: NextJS static build served by FastAPI at `/`.
- Backend: Python FastAPI.
- Packaging: one Docker container for local use.
- Python package manager in Docker: `uv`.
- Database: local SQLite database, created automatically when missing.
- Authentication: hardcoded MVP credentials `user` and `password`, with database support for multiple users later.
- AI provider: DeepSeek native API.
- AI environment variable: `DEEPSEEK_API_KEY` from the project root `.env`.
- AI model: `deepseek-v4-pro`.
- Existing frontend: `frontend/` already contains a working frontend-only Kanban demo with NextJS, React, Vitest, and Playwright.

## General Working Rules

- [ ] Read `AGENTS.md` before starting each phase.
- [ ] Keep each phase scoped to the phase goal.
- [ ] Identify root cause before fixing any issue.
- [ ] Prefer simple implementation over abstractions.
- [ ] Keep README and docs concise.
- [ ] Do not use emojis.
- [ ] Confirm current package versions from official docs or the package manager when adding or upgrading dependencies.
- [ ] Preserve user changes already present in the worktree.
- [ ] Record important design choices in `docs/`.

## Phase 1: Plan

Goal: turn this document into an approved execution plan before feature work begins.

### Tasks

- [ ] Review root `AGENTS.md`.
- [ ] Review the existing `frontend/` structure and scripts.
- [ ] Review existing placeholder docs such as `backend/AGENTS.md` and `scripts/AGENTS.md`.
- [ ] Expand this plan with tasks, tests, success criteria, and approval points.
- [ ] Include a planned task to create or update `frontend/AGENTS.md` after the plan is approved.
- [ ] Correct obvious spelling and terminology issues, including `SQLite`.
- [ ] Ask the user to review and approve this plan before Phase 2 begins.

### Tests

- [ ] No code tests required for this phase.
- [ ] Verify the plan is internally consistent with root `AGENTS.md`.
- [ ] Verify AI provider references use DeepSeek, not OpenRouter.

### Success Criteria

- [ ] The plan has clear phases, checklists, tests, and success criteria.
- [ ] Any approval points are explicit.
- [ ] The user approves moving to Phase 2.

### Approval

- User approval required before starting Phase 2.

## Phase 2: Scaffolding

Goal: create the local backend, Docker, and scripts foundation with a minimal static page and API call.

### Tasks

- [x] Create the FastAPI backend structure in `backend/`.
- [x] Update `backend/AGENTS.md` with the backend layout, commands, and conventions.
- [x] Add minimal backend endpoints:
  - [x] `GET /` serves example static HTML.
  - [x] `GET /api/health` returns a simple JSON health response.
- [x] Add Python project files for the backend using `uv`.
- [x] Add Docker infrastructure for running the app locally.
- [x] Add start and stop scripts in `scripts/` for macOS, Windows, and Linux.
- [x] Update `scripts/AGENTS.md` with script expectations.
- [x] Add minimal backend tests for the health endpoint and static page.
- [x] Keep documentation minimal but sufficient to run the scaffold.

### Tests

- [x] Run backend unit tests.
- [x] Build the Docker image.
- [x] Start the app with the platform script or documented Docker command.
- [x] Verify `GET /` returns the example HTML.
- [x] Verify `GET /api/health` returns JSON.
- [x] Stop the app with the platform script.

### Success Criteria

- [x] The app runs locally in Docker.
- [x] Static HTML is served at `/`.
- [x] A backend API route works.
- [x] Start and stop scripts work or have documented platform limitations.
- [x] Tests pass.

## Phase 3: Add Existing Frontend

Goal: statically build the existing NextJS frontend and serve it from FastAPI.

### Tasks

- [x] Create or update `frontend/AGENTS.md` to describe the existing frontend code, scripts, components, tests, and conventions.
- [x] Configure NextJS for static export if required.
- [x] Update Docker build steps to install frontend dependencies and build the static frontend.
- [x] Update FastAPI static file serving so `/` shows the Kanban demo.
- [x] Ensure NextJS static assets are served correctly.
- [x] Preserve existing frontend behavior.
- [x] Add or update integration coverage for serving the built frontend through FastAPI.

### Tests

- [x] Run `npm run lint` in `frontend/`.
- [x] Run `npm run test:unit` in `frontend/`.
- [x] Run `npm run test:e2e` in `frontend/` where supported.
- [x] Run backend tests.
- [x] Build Docker image.
- [x] Start Docker app and verify `/` displays the demo Kanban board.

### Success Criteria

- [x] Existing Kanban demo appears at `/` through FastAPI.
- [x] Static assets load without 404 errors.
- [x] Existing drag and edit behavior still works.
- [x] Unit and integration tests pass.

## Phase 4: Fake User Sign In

Goal: require login with hardcoded MVP credentials before showing the Kanban board.

### Tasks

- [x] Add a simple login screen to the frontend.
- [x] Accept only username `user` and password `password`.
- [x] Add a logout control.
- [x] Keep the session mechanism simple and local to the MVP.
- [x] Ensure unauthenticated users see login first when visiting `/`.
- [x] Ensure authenticated users see the Kanban board.
- [x] Add frontend tests for login failure, login success, and logout.
- [x] Add backend support only if needed for the chosen session approach.

### Tests

- [x] Run frontend unit tests.
- [x] Run frontend e2e tests for login and logout.
- [x] Run backend tests if backend auth/session code is added.
- [x] Verify Docker app starts and login flow works manually.

### Success Criteria

- [x] Visiting `/` requires login.
- [x] `user` / `password` shows the Kanban board.
- [x] Invalid credentials do not show the Kanban board.
- [x] Logout returns to the login screen.
- [x] Tests pass.

## Phase 5: Database Modeling

Goal: design the SQLite schema and Kanban JSON shape before implementing persistence.

### Tasks

- [x] Propose a simple SQLite schema that supports multiple users later.
- [x] Store each user's single MVP Kanban board as JSON.
- [x] Define the Kanban JSON shape:
  - [x] columns
  - [x] cards
  - [x] column order
  - [x] card order
  - [x] timestamps if needed
- [x] Define how default board data is created for a new user.
- [x] Define minimal validation rules for board JSON.
- [x] Document the database approach in `docs/DATABASE.md`.
- [x] Ask the user to review and approve the database approach before Phase 6.

### Tests

- [x] No implementation tests required before approval.
- [x] Review the schema against the MVP requirements.
- [x] Check that the schema does not block future multiple-user support.

### Success Criteria

- [x] `docs/DATABASE.md` explains the schema and JSON format.
- [x] The approach supports one board per signed-in user for the MVP.
- [x] The approach can support multiple users later.
- [x] The user approves moving to Phase 6.

### Approval

- User approval required before starting Phase 6.

## Phase 6: Backend Persistence API

Goal: add backend routes to read and update the Kanban board for a user.

### Tasks

- [x] Add SQLite initialization that creates the database if missing.
- [x] Add user and board persistence based on the approved schema.
- [x] Add API routes for:
  - [x] reading the current user's board
  - [x] replacing or updating the current user's board
  - [x] health checking the backend
- [x] Add simple validation for board JSON.
- [x] Add deterministic default board creation for the MVP user.
- [x] Keep API responses small and predictable.
- [x] Add backend unit tests for database initialization, default board creation, read, update, and validation errors.

### Tests

- [x] Run backend unit tests with a temporary SQLite database.
- [x] Run API tests through FastAPI's test client.
- [x] Verify a missing database is created automatically.
- [x] Verify data persists across backend restarts in Docker.

### Success Criteria

- [x] Backend can create, read, and update the MVP user's board.
- [x] SQLite database is created when missing.
- [x] Invalid board data is rejected with a clear error.
- [x] Backend tests pass.

## Phase 7: Frontend And Backend Integration

Goal: make the frontend use the backend API so the Kanban board is persistent.

### Tasks

- [x] Replace frontend-only demo state with API-backed board loading.
- [x] Save card edits, card moves, card creation, and column renames through the backend API.
- [x] Add loading and error states that are simple and unobtrusive.
- [x] Keep drag and drop behavior intact.
- [x] Ensure logout/login does not destroy persisted board data.
- [x] Add frontend integration tests around API-backed behavior.
- [x] Add e2e tests for persistence across page reloads.

### Tests

- [x] Run frontend unit tests.
- [x] Run frontend e2e tests.
- [x] Run backend tests.
- [x] Run Docker app and manually verify changes persist after refresh.
- [x] Restart the Docker app and verify persisted data remains.

### Success Criteria

- [x] The Kanban board is loaded from the backend.
- [x] User changes are saved to SQLite.
- [x] Refreshing the browser preserves the board.
- [x] Restarting the app preserves the board.
- [x] Tests pass.

## Phase 8: AI Connectivity

Goal: verify the backend can call DeepSeek through the native API.

### Tasks

- [ ] Load `DEEPSEEK_API_KEY` from the project root `.env`.
- [ ] Add a small backend service for DeepSeek calls.
- [ ] Use model `deepseek-v4-pro`.
- [ ] Add a test-only or development-only endpoint/command for a simple connectivity check.
- [ ] Run a simple `2+2` test to verify the model responds.
- [ ] Avoid logging secrets.
- [ ] Document required environment variables.

### Tests

- [ ] Run backend unit tests with the DeepSeek client mocked.
- [ ] Run the real connectivity check when `DEEPSEEK_API_KEY` is available.
- [ ] Verify missing API key produces a clear local error.

### Success Criteria

- [ ] Backend can make a real DeepSeek call when configured.
- [ ] The `2+2` check returns a sensible answer.
- [ ] Tests do not require a real API key unless explicitly marked as connectivity tests.
- [ ] Secrets are not printed in logs.

## Phase 9: AI Kanban Structured Output

Goal: send board context and chat history to the AI and accept structured responses that may update the Kanban.

### Tasks

- [ ] Define the AI request payload:
  - [ ] current Kanban JSON
  - [ ] user question
  - [ ] conversation history
- [ ] Define the AI structured response format:
  - [ ] assistant message
  - [ ] optional Kanban update
  - [ ] optional explanation or operation summary if useful
- [ ] Implement backend prompt construction.
- [ ] Validate AI responses before changing the database.
- [ ] Apply AI board updates only after validation passes.
- [ ] Store or return conversation history according to the simplest MVP approach.
- [ ] Add tests for AI response parsing, valid updates, invalid updates, and no-update replies.

### Tests

- [ ] Run backend unit tests with mocked AI responses.
- [ ] Test card creation through structured output.
- [ ] Test card editing through structured output.
- [ ] Test card movement through structured output.
- [ ] Test invalid AI output is rejected without changing the board.
- [ ] Run a real AI smoke test when `DEEPSEEK_API_KEY` is available.

### Success Criteria

- [ ] AI receives the current board, user message, and conversation context.
- [ ] AI can return a user-facing response without changing the board.
- [ ] AI can return a valid board update that is saved.
- [ ] Invalid AI updates do not corrupt persisted data.
- [ ] Tests pass.

## Phase 10: AI Chat Sidebar

Goal: add a polished sidebar chat experience that lets the AI help manage the Kanban board.

### Tasks

- [ ] Add a sidebar chat widget to the existing UI.
- [ ] Match the project color scheme from `AGENTS.md`.
- [ ] Support sending messages and rendering assistant replies.
- [ ] Show simple loading and error states.
- [ ] Call the backend AI endpoint.
- [ ] Refresh the Kanban board automatically when the AI updates it.
- [ ] Preserve drag and drop and manual editing behavior.
- [ ] Add frontend tests for chat rendering and message sending.
- [ ] Add e2e tests for an AI-assisted board update with the AI mocked.
- [ ] Verify responsive layout on desktop and mobile.

### Tests

- [ ] Run frontend lint.
- [ ] Run frontend unit tests.
- [ ] Run frontend e2e tests.
- [ ] Run backend tests.
- [ ] Run Docker app and manually verify the chat sidebar.
- [ ] Verify AI board updates refresh the UI automatically.

### Success Criteria

- [ ] Chat sidebar is visible and usable.
- [ ] User can send messages and see AI responses.
- [ ] AI can create, edit, or move cards through structured output.
- [ ] UI refreshes after AI updates the board.
- [ ] Layout remains usable on supported screen sizes.
- [ ] Tests pass.

## Final MVP Acceptance

- [ ] App runs locally in one Docker container.
- [ ] User can sign in with `user` and `password`.
- [ ] User can log out.
- [ ] User sees one persistent Kanban board.
- [ ] Fixed columns can be renamed.
- [ ] Cards can be moved with drag and drop.
- [ ] Cards can be edited.
- [ ] AI chat sidebar can create, edit, and move one or more cards.
- [ ] SQLite database is created automatically if missing.
- [ ] Start and stop scripts exist for macOS, Windows, and Linux.
- [ ] Core backend and frontend tests pass.
