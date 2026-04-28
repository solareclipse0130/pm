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

For full manual MVP verification, follow `docs/ACCEPTANCE.md` or `docs/ACCEPTANCE.zh.md`.

## Ports

The app listens on port `8000` inside the Docker container. The start scripts publish that container port to host port `9000` by default:

```text
localhost:9000 -> container:8000
```

`EXPOSE 8000` in the Dockerfile documents the container port. It does not force the host port. Change the host port with `PORT`:

Linux or macOS:

```sh
PORT=9010 ./scripts/start-linux.sh
```

Windows PowerShell:

```powershell
$env:PORT = "9010"
.\scripts\start-windows.ps1
```

Then open `http://localhost:9010`.

## Docker Desktop And WSL

If the Linux script cannot reach Docker from WSL:

- Start Docker Desktop in Windows first.
- In Docker Desktop, enable WSL integration for the current distro.
- Run `docker version` inside WSL and confirm both client and server are shown.
- If port forwarding is stuck, use Docker Desktop `Troubleshoot > Restart Docker Desktop`.
- If Windows asks whether Docker can access the network, allow it.
- If host port `9000` is busy, start with another `PORT`.

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
