# Frontend

This directory contains the existing NextJS Kanban demo for the Project Management MVP.

## Structure

- `src/app/` contains the NextJS app entrypoints and global styles.
- `src/components/` contains Kanban UI components.
- `src/lib/` contains board data helpers, movement logic, and API clients.
- `tests/` contains Playwright end-to-end tests.
- `public/` contains static public assets.

## Commands

From `frontend/`:

- Install dependencies: `npm install`
- Run locally: `npm run dev`
- Build static export: `npm run build`
- Run lint: `npm run lint`
- Run unit tests: `npm run test:unit`
- Run end-to-end tests: `npm run test:e2e`

## Conventions

- Keep the frontend as a static export so FastAPI can serve it from `/`.
- Preserve existing drag, edit, add, and delete behavior unless a phase explicitly changes it.
- Keep styling aligned with the project color scheme in the root `AGENTS.md`.
- Avoid introducing server-only NextJS features while the Docker app serves static files.
- Keep the AI chat sidebar API-backed and update the visible board when the backend returns a board update.
