# Running The Local App

The Docker app builds the static NextJS frontend and serves it through FastAPI.
SQLite data is stored in project root `data/app.db` when the Docker scripts are used.

## macOS

```sh
./scripts/start-mac.sh
./scripts/stop-mac.sh
```

## Linux

```sh
./scripts/start-linux.sh
./scripts/stop-linux.sh
```

## Windows PowerShell

```powershell
.\scripts\start-windows.ps1
.\scripts\stop-windows.ps1
```

The app is available at `http://localhost:9000` by default. Set `PORT` before running the start script to use another host port.

## Environment

Set `DEEPSEEK_API_KEY` in the project root `.env` for AI calls. The backend also accepts the same variable from the process environment.

## Sign In

The MVP login is local-only and hardcoded to `user` / `password`. It is not production authentication. See `docs/AUTH.md` for the current boundary and future production work.

## DeepSeek Check

With the app running, check AI connectivity:

```sh
curl http://localhost:9000/api/dev/deepseek-check
```

The response includes the model and answer only. It must not include the API key.

The AI chat backend endpoint is `POST /api/ai/chat`. See `docs/AI.md` for the request and response shape.
