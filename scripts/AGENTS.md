# Scripts

This directory contains platform scripts for running the local Docker app.

## Files

- `start-linux.sh` builds and runs the Docker container on Linux.
- `stop-linux.sh` stops and removes the Docker container on Linux.
- `start-mac.sh` builds and runs the Docker container on macOS.
- `stop-mac.sh` stops and removes the Docker container on macOS.
- `start-windows.ps1` builds and runs the Docker container on Windows PowerShell.
- `stop-windows.ps1` stops and removes the Docker container on Windows PowerShell.

## Behavior

- The Docker image name is `pm-mvp`.
- The Docker container name is `pm-mvp`.
- The host port defaults to `9000`.
- Set `PORT` to override the host port.
- Start scripts create and mount project root `data/` at `/app/data` so SQLite persists across container rebuilds.
- If a project root `.env` file exists, start scripts normalize surrounding whitespace and pass a temporary env file to Docker with `--env-file`.
