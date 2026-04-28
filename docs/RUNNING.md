# Running The Local App

The Docker app builds the static NextJS frontend and serves it through FastAPI.

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
