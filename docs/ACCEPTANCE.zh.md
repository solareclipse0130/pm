# 手动验收清单

这份清单用于在代码变更后，手动验证本地 MVP 是否仍然正常。

## 测试前准备

- 如果你使用 Windows 或 WSL，先启动 Docker Desktop。
- 如果要测试 AI，确认项目根目录 `.env` 中已经设置 `DEEPSEEK_API_KEY`。
- 如果想完整保留当前看板数据，先备份 `data/app.db`。

## 启动应用

Linux：

```sh
./scripts/start-linux.sh
```

macOS：

```sh
./scripts/start-mac.sh
```

Windows PowerShell：

```powershell
.\scripts\start-windows.ps1
```

打开 `http://localhost:9000`。

预期结果：

- 应用可以在浏览器中打开。
- 首先显示登录页面。

## 登录与登出

1. 输入用户名 `user`。
2. 输入密码 `password`。
3. 点击 `Sign in`。
4. 点击 `Logout`。

预期结果：

- 正确凭据会进入 Kanban 看板。
- 登出后回到登录页面。

可选反向检查：

1. 输入用户名 `user`。
2. 输入密码 `wrong`。
3. 点击 `Sign in`。

预期结果：

- 不会显示看板。
- 页面显示凭据错误提示。

## Kanban 看板

登录后验证：

- 可以看到 5 个固定列。
- 可以看到已有卡片。
- 可以看到 `Board Assistant` 侧边栏。

## 手动修改看板

重命名列：

1. 修改第一列标题。
2. 等待保存状态显示修改已保存。
3. 刷新浏览器。

预期结果：

- 刷新后列名仍然保留。

创建并编辑卡片：

1. 在任意列新增一张卡片。
2. 编辑它的标题或详情。
3. 刷新浏览器。

预期结果：

- 新卡片仍然存在。
- 编辑后的文字仍然保留。

移动卡片：

1. 将一张卡片从一个列拖到另一个列。
2. 等待保存状态显示修改已保存。
3. 刷新浏览器。

预期结果：

- 卡片仍然位于新的列中。

## 重启后的持久化

1. 对看板做一个小修改。
2. 停止应用。
3. 重新启动应用。
4. 再次登录。

预期结果：

- 之前的看板修改仍然存在。
- 项目根目录下存在 `data/app.db`。

## AI 侧边栏

发送一个不修改看板的请求：

```text
Briefly summarize the current board. Do not change the board.
```

预期结果：

- assistant 会回复。
- 看板不会改变。

发送一个会修改看板的请求：

```text
Create a card in Backlog titled Manual AI Test with details Created during manual acceptance.
```

预期结果：

- assistant 会回复。
- 看板上出现 `Manual AI Test` 卡片。
- 刷新浏览器后卡片仍然存在。

可选 AI 组合检查：

```text
Create a card titled AI Follow Up in Backlog, edit Manual AI Test details to Verified, and move Manual AI Test to Done.
```

预期结果：

- assistant 会回复。
- 卡片按要求被编辑并移动。
- 如果 AI 选择追问澄清，则不会保存无效看板更新。

## API 检查

应用运行时执行：

```sh
curl http://localhost:9000/api/health
curl http://localhost:9000/api/board
curl http://localhost:9000/api/dev/deepseek-check
```

预期结果：

- health 返回 `{"status":"ok"}`。
- board 返回包含 `version`、`columns` 和 `cards` 的 JSON。
- DeepSeek 检查返回模型和答案，但绝不会返回 API key。

## 自动化检查

后端：

```sh
cd backend
../.venv/bin/uv run --extra dev pytest
cd ..
```

前端：

```sh
cd frontend
npm run lint
npm run test:unit
npm run test:e2e
npm run build
cd ..
```

预期结果：

- 所有测试和构建都通过。

## 停止应用

Linux：

```sh
./scripts/stop-linux.sh
```

macOS：

```sh
./scripts/stop-mac.sh
```

Windows PowerShell：

```powershell
.\scripts\stop-windows.ps1
```

预期结果：

- `pm-mvp` 容器停止。
