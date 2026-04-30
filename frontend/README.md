# Frontend (Kanban Studio)

Built into static files and served by the FastAPI backend at `/`. To run the
full app, see [`../docs/RUNNING.md`](../docs/RUNNING.md).

## Local iteration

`npm run dev` works for UI iteration, but live API calls (`/api/board`,
`/api/ai/chat`) will fail unless the backend is also running. For pure UI
development, prefer the unit tests in `src/` and the e2e tests in `tests/`,
which mock the backend.

## Tests

```sh
npm run lint
npm run test:unit
npm run test:e2e
```

For a static-export build (used by the Docker image) run `npm run build`.
