# 运行本地应用

Docker 应用会构建静态 NextJS 前端，并通过 FastAPI 提供服务。
使用 Docker 脚本时，SQLite 数据会保存在项目根目录的 `data/app.db`。

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

应用默认访问地址是 `http://localhost:9000`。如果需要使用其他宿主机端口，可以在启动脚本前设置 `PORT`。

完整手动 MVP 验收请查看 `docs/ACCEPTANCE.md` 或 `docs/ACCEPTANCE.zh.md`。

## 端口

应用在 Docker 容器内部监听 `8000` 端口。启动脚本默认把容器内的 `8000` 映射到宿主机的 `9000`：

```text
localhost:9000 -> container:8000
```

Dockerfile 里的 `EXPOSE 8000` 只是说明容器内部端口，不会强制宿主机也使用 `8000`。如需修改宿主机端口，可以设置 `PORT`。

Linux 或 macOS：

```sh
PORT=9010 ./scripts/start-linux.sh
```

Windows PowerShell：

```powershell
$env:PORT = "9010"
.\scripts\start-windows.ps1
```

然后打开 `http://localhost:9010`。

## Docker Desktop 与 WSL

如果在 WSL 中运行 Linux 脚本时无法连接 Docker：

- 先在 Windows 中启动 Docker Desktop。
- 在 Docker Desktop 中为当前 WSL 发行版启用 WSL integration。
- 在 WSL 里运行 `docker version`，确认能看到 client 和 server。
- 如果端口转发卡住，使用 Docker Desktop 的 `Troubleshoot > Restart Docker Desktop`。
- 如果 Windows 弹出 Docker 网络访问请求，选择允许。
- 如果宿主机端口 `9000` 被占用，换一个 `PORT` 启动。

## 环境变量

如果要使用 AI，请在项目根目录 `.env` 中设置 `DEEPSEEK_API_KEY`。后端也可以从进程环境变量读取同名变量。

## 登录

MVP 登录仅用于本地测试，硬编码为 `user` / `password`。这不是生产认证。当前边界和未来生产化工作见 `docs/AUTH.md`。

## DeepSeek 检查

应用运行后，可以检查 AI 连接：

```sh
curl http://localhost:9000/api/dev/deepseek-check
```

响应只包含模型和答案，不能包含 API key。

AI 聊天后端端点是 `POST /api/ai/chat`。请求和响应格式见 `docs/AI.md`。
