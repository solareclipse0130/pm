# Manual Acceptance Checklist

Use this checklist to manually verify the local MVP after code changes.

## Before Testing

- Start Docker Desktop if you are using Windows or WSL.
- Confirm `DEEPSEEK_API_KEY` is set in the project root `.env` if testing AI.
- Back up `data/app.db` first if you want to preserve the current board exactly.

## Start The App

Linux:

```sh
./scripts/start-linux.sh
```

macOS:

```sh
./scripts/start-mac.sh
```

Windows PowerShell:

```powershell
.\scripts\start-windows.ps1
```

Open `http://localhost:9000`.

Expected result:

- The app loads in the browser.
- The sign-in screen is shown first.

## Sign In And Out

1. Enter username `user`.
2. Enter password `password`.
3. Click `Sign in`.
4. Click `Logout`.

Expected result:

- Valid credentials show the Kanban board.
- Logout returns to the sign-in screen.

Optional negative check:

1. Enter username `user`.
2. Enter password `wrong`.
3. Click `Sign in`.

Expected result:

- The board is not shown.
- An invalid credentials message appears.

## Kanban Board

After signing in, verify:

- Five fixed columns are visible.
- Existing cards are visible.
- The `Board Assistant` sidebar is visible.

## Manual Board Changes

Rename a column:

1. Change the first column title.
2. Wait until the save status says changes are saved.
3. Refresh the browser.

Expected result:

- The renamed column remains after refresh.

Create and edit a card:

1. Add a card in any column.
2. Edit its title or details.
3. Refresh the browser.

Expected result:

- The new card remains.
- The edited text remains.

Move a card:

1. Drag a card from one column to another.
2. Wait until the save status says changes are saved.
3. Refresh the browser.

Expected result:

- The card remains in the new column.

## Persistence Across Restart

1. Make a small board change.
2. Stop the app.
3. Start the app again.
4. Sign in.

Expected result:

- The previous board change is still present.
- `data/app.db` exists in the project root.

## AI Sidebar

Send a non-changing prompt:

```text
Briefly summarize the current board. Do not change the board.
```

Expected result:

- The assistant replies.
- The board does not change.

Send a board-changing prompt:

```text
Create a card in Backlog titled Manual AI Test with details Created during manual acceptance.
```

Expected result:

- The assistant replies.
- A `Manual AI Test` card appears on the board.
- Refreshing the browser keeps the card.

Optional combined AI check:

```text
Create a card titled AI Follow Up in Backlog, edit Manual AI Test details to Verified, and move Manual AI Test to Done.
```

Expected result:

- The assistant replies.
- The card is edited and moved as requested.
- If the AI asks for clarification instead, no invalid board update is saved.

## API Checks

With the app running:

```sh
curl http://localhost:9000/api/health
curl http://localhost:9000/api/board
curl http://localhost:9000/api/dev/deepseek-check
```

Expected result:

- Health returns `{"status":"ok"}`.
- Board returns JSON with `version`, `columns`, and `cards`.
- DeepSeek check returns a model and answer, but never returns the API key.

## Automated Checks

Backend:

```sh
cd backend
../.venv/bin/uv run --extra dev pytest
cd ..
```

Frontend:

```sh
cd frontend
npm run lint
npm run test:unit
npm run test:e2e
npm run build
cd ..
```

Expected result:

- All tests and builds pass.

## Stop The App

Linux:

```sh
./scripts/stop-linux.sh
```

macOS:

```sh
./scripts/stop-mac.sh
```

Windows PowerShell:

```powershell
.\scripts\stop-windows.ps1
```

Expected result:

- The `pm-mvp` container stops.
