# 代码审查报告

审查日期：2026-04-30
审查范围：commit `4ae71e9` 主分支全仓
审查者：Claude（Opus 4.7）

## 1. 审查范围与基础

- **后端**：`backend/app/{main,storage,ai,deepseek}.py` 与 `backend/tests/`（共 36 项测试）
- **前端**：`frontend/src/{app,components,lib}/`、`frontend/src/test/setup.ts`、`frontend/tests/kanban.spec.ts`（14 单元 + 9 e2e）
- **基础设施**：`Dockerfile`、`.dockerignore`、`scripts/`（六个启停脚本）
- **配置**：`pyproject.toml`、`package.json`、`tsconfig.json`、`vitest.config.ts`、`playwright.config.ts`、`eslint.config.mjs`、`next.config.ts`
- **文档**：`AGENTS.md`（根/backend/frontend/scripts）、`docs/`、`strategy/`、`CLAUDE.md`

测试基线（本次审查前已跑通）：

| 套件 | 结果 |
|---|---|
| 后端 pytest | 36/36 通过 |
| 前端 ESLint | 0 错误 |
| 前端 Vitest | 14/14 通过 |
| 前端 next build | 成功 |
| Playwright e2e | 9/9 通过 |

未跑：Docker 镜像构建、`/api/dev/deepseek-check` 真实连通性。

---

## 2. 总评

代码量小、目标清晰，**MVP 边界把握很好**：模块平铺、责任单一、抽象克制、测试覆盖到位。AI 路径用「严格 JSON schema 校验 + 长度上限 + 乐观并发 409」三道闸，比一般 demo 强不少。

主要风险集中在两类：

1. **后端阻塞 I/O**：DeepSeek 客户端用同步 `httpx.post`，在 FastAPI 线程池里会卡 30s，多人/高并发场景会饿死 worker。
2. **前端没有节流/去抖**：列重命名按 `onChange` 触发整板 PUT，每个按键都打一次接口，单用户也明显浪费。

其余多数是代码质量改进、未来版本的演进点，或者已在 `AGENTS.md`/`docs/AUTH.md` 中明确说明的 MVP 妥协。

报告把每个发现按 **P1（v0.2 之前必修）/ P2（建议修）/ P3（改进项）/ OK-for-MVP（已记录的妥协）** 标注。

---

## 3. 后端审查

### 3.1 `backend/app/main.py`

**P2 — `DEEPSEEK_API_KEY` 缺失返回 400 语义不当**
`main.py:102-103`、`main.py:111-112` 把 `DeepSeekConfigurationError` 都映射到 HTTP 400。这是服务端配置问题，不是客户端请求问题，应该是 503（Service Unavailable）或 500。当前对外暴露 400 会让前端把它当成「用户输入错误」展示。

```python
# main.py:102
except DeepSeekConfigurationError as error:
    raise HTTPException(status_code=400, detail=str(error)) from error
```
建议：改为 503，并在前端针对 503 做单独的「AI 未配置」提示。

**P3 — `payload: dict[str, Any] = Body(...)` 跳过 Pydantic**
`main.py:56`、`main.py:63` 都直接收 `dict`，把校验完全推到了 `validate_board` / `validate_user_message`。这在 MVP 范围内可接受，但放弃了 FastAPI 自动文档（OpenAPI schema 里看不出参数结构）。`docs/AI.md` 已经手写了 schema，可以接受；但 v0.3 加真实多用户时，建议引入 Pydantic 模型。

**P3 — `read_board` 没有 try/except**
`main.py:51-53`：理论上 `get_or_create_board` 内部 `validate_board` 只校验默认看板，正常不会抛。但若运维直接修改了 `app.db` 中的 JSON，前端会拿到 500 而不是结构化错误。建议加 `ValueError → 500`。低优先级，因为正常路径不会触发。

**OK-for-MVP — 409 检查的 TOCTOU 窗口**
`main.py:75-85` 重读 board 与 `save_board` 是两次独立 SQLite 事务，中间仍可能被插入。`docs/AI.md` §"Reliability Boundaries" 已经声明这是最小化保障。等真实多用户时再考虑用 `BEGIN IMMEDIATE` 把读+写包进一个事务，或者给 `boards` 表加 `version` 字段做乐观锁。

### 3.2 `backend/app/storage.py`

**P2 — `get_or_create_board` 在并发下可能重复插入**
`storage.py:199-223`：当一个用户没有 board 时，两个并发请求都会读到空、各自 `create_default_board`、然后第二个 `INSERT` 会被 `boards.user_id UNIQUE` 拒绝并抛 `IntegrityError`。MVP 单用户单浏览器场景几乎触发不到，但写法不够「正确」。

修复成本很低：把 `INSERT` 改成 `INSERT ... ON CONFLICT(user_id) DO NOTHING`，再 `SELECT` 一次拿到结果。

**P3 — `initialize_database` 在每次 `get_or_create_board` / `save_board` 都被调用**
`storage.py:203` 和 `storage.py:232`。`CREATE TABLE IF NOT EXISTS` 是幂等的，开销可忽略，但语义上应该在应用启动时调用一次。建议在 `create_app` 里调用一次，业务函数里删掉。

**P3 — `get_or_create_user` 的 `ON CONFLICT DO UPDATE SET updated_at = users.updated_at` 是无操作**
`storage.py:184-191`：这个写法是为了让 ON CONFLICT 路径走通，但 `SET` 的值就是当前值。可以用 `ON CONFLICT(username) DO NOTHING`，再用 `SELECT` 拿 id，更直观。

**P3 — `validate_board` 没有上限保护**
对 `columns` 数量、`cards` 数量、字符串长度都没有上限。AI 理论上可以返回一个巨大的 board 把 DB 撑爆。MVP 风险极低。需要时加 `len(columns) <= 50`、`len(cards) <= 1000`、`len(title) <= 200` 之类即可。

**OK-for-MVP — 默认 board 数据与前端 `kanban.ts initialData` 重复**
后端 `storage.py:57-118` 与前端 `lib/kanban.ts:21-92` 各维护一份默认 board。`CLAUDE.md` 已经标注「id 必须保持一致」。前端 `initialData` 实际只用于单元测试，运行时 board 始终从后端取。可以接受，但 v0.2 起建议把前端 `initialData` 直接 `import` 一份测试 fixture，或者完全删掉（测试里直接用对象字面量）。

### 3.3 `backend/app/ai.py`

**P2 — 在 `assistantMessage` 与 `operationSummary` 上没有长度上限**
`ai.py:104-117`：用户消息和历史项各 2000 字上限，但 AI 回的 `assistantMessage` 和 `operationSummary` 只校验类型不校验长度。模型抽风返回 50KB 文本会原样落到前端。建议加同样的 2000 字截断。

**P3 — `set(parsed) != REQUIRED_RESPONSE_KEYS` 的相等性检查过严**
`ai.py:99` 用集合相等会拒绝任何额外字段。这能防止模型「污染」结构化输出，但也意味着 DeepSeek 升级后多返回一个无关字段就会让所有请求失败。可以放宽成「必含 REQUIRED 键集」并忽略额外键。是个权衡，目前选择是合理的，标 P3。

**P3 — 历史中夹带过期 board 上下文**
`ai.py:70-88`：每次请求把当前 board JSON 作为单独的 user message，再把 history 拼在后面。history 里的 user 消息本身没有 board snapshot；assistant 历史回复里也不会重复 board JSON。这个设计是对的（避免重复带 board 浪费 token），但在 prompt 顺序上是「system → 当前 board → 旧对话 → 新用户消息」，模型可能误以为旧对话发生在「当前 board」之上。低概率影响，但值得在 prompt 里多一句「Old conversation may reference earlier board states」。

**OK-for-MVP — 没有重试**
模型偶发返回不合法 JSON 会直接 502。MVP 接受，下一步可以加一次「请只返回有效 JSON」的二次尝试。

### 3.4 `backend/app/deepseek.py`

**P1 — 同步 `httpx.post` 阻塞 FastAPI 线程池**
`deepseek.py:79-84`：FastAPI 把同步路由跑在 anyio threadpool（默认 40 线程）。`/api/ai/chat` 的 30s 超时意味着，41 个并发 AI 请求就会让所有 worker 阻塞，连 `/api/health` 这种瞬时接口都会排队。

改造：

```python
async def create_chat_completion(...) -> str:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(...)
```

并把 `main.py:62` 的 `def ai_chat` 改成 `async def`，把 `ask_ai_for_board_update` 也异步化。

本地单用户 MVP 不会触发，但这是一个很容易因为「demo 跑得通」就被遗忘的坑，**v0.3 多用户上线之前必须改**。

**P3 — `read_root_env_value` 自实现 .env 解析**
`deepseek.py:25-40`：手写 `.env` 解析能跑，但不处理：

- 引号内的 `=`（次要）
- 行内 `#` 注释（如 `KEY=value # note` 会把 `# note` 当成 value）
- 单边引号（`'value` → 会被 strip 成 `value`，错误）

建议直接用 `python-dotenv`（轻依赖）。或者保留自实现，但写明已知限制。

**P3 — `thinking: {"type": "disabled"}` 是供应商私有字段**
`deepseek.py:68`：这是 DeepSeek 当前 API 接受的字段，但写在通用客户端里耦合度有点高，且没注释说明为什么禁用。加一行注释或抽出常量更好。

### 3.5 后端测试

整体覆盖率高，36 项测试组织清晰：

- `test_main.py` 覆盖了所有 7 条路由的成功与失败路径，包括 409 并发场景（`test_ai_chat_rejects_update_when_board_changed_during_ai_call`）。
- `test_ai.py` 把 `parse_ai_response` 的 happy/sad path 都覆盖到。
- `test_deepseek.py` 用 monkeypatch httpx.post，避免真实网络调用。

**P3 — 没有 `validate_board` 的直接单元测试**
现在通过 `PUT /api/board` 间接覆盖。`storage.py:121-179` 校验规则有十多条，但 `test_board_api_rejects_invalid_board` 只覆盖了「missing card」一条。建议加一组专门测 `validate_board` 各种失败情形的参数化测试。

---

## 4. 前端审查

### 4.1 `src/components/AppShell.tsx`

**P3 — 登录态用 localStorage flag，可在 DevTools 直接绕过**
`AppShell.tsx:6-15`：完全符合 MVP 设计（`docs/AUTH.md` 明确说这不是真鉴权），但建议在登录界面加一行小字「Local demo only」让用户知情。**不建议在 MVP 阶段做任何「假装防御」的工作**——`AGENTS.md` 已经禁止过度防御。

### 4.2 `src/components/KanbanBoard.tsx`

**P1 — 列重命名每个按键都打 PUT 接口**
`KanbanBoard.tsx:151-158` 与 `KanbanColumn.tsx:46-51`：`onChange` 直接 `updateBoard`，没有去抖。输入「Persisted Backlog」这 17 个字符就是 17 次 PUT、17 次 SQLite 写入、17 次整板 JSON 序列化。e2e 测试 `persists changes across reloads` 也是依赖这个行为通过的，但这显然不对。

建议：用 `useRef` + 200~500ms debounce 包一层，或者改成 `onBlur` 触发保存。改完要同步更新 `kanban.spec.ts:181-187`。

**P2 — 多次 `updateBoard` 间没有请求排队**
`KanbanBoard.tsx:116-131`：每次本地更新都 `setSaveStatus("saving")` 后异步 `saveBoard`。如果用户拖卡片 + 编辑 + 拖卡片快速操作，3 个请求并发飞出，到达后端的顺序不保证，**最后到达的请求决定最终状态**——可能是中间那次旧状态覆盖了最新。

修复方案有两个：

1. 用 promise chain（`saveQueueRef`）保证串行；
2. 接受最终一致性，但在请求 body 里带上 `version` 让后端拒绝旧版本（需要后端配合）。

P2 而非 P1，因为单人手动操作很难触发。

**P2 — `getChangedCardIds` 不识别新增列或被删除卡片**
`KanbanBoard.tsx:36-57`：只遍历 `Object.entries(next.cards)`。如果 AI 删除了一张卡，那张卡就不在 `next.cards` 里、也不会被高亮。如果 AI 重命名了某列，没有视觉提示。MVP 范围内 AI 提示词不让删卡，但代码里不阻止。

**P3 — `loadBoard().catch` 把状态置成 "error" 但 UI 没明显反馈**
`KanbanBoard.tsx:89-92`：失败时 `saveStatus="error"`、`board=null`、`isLoading=false`，最终渲染走到 `!board` 分支显示「Unable to load board.」。能用，但 `saveStatus` 名字不对——这是「load 失败」，不是「save 失败」。建议引入独立的 `loadStatus`。

**P3 — `activeCardId as string` 强转**
`KanbanBoard.tsx:134`、`KanbanBoard.tsx:147`：dnd-kit 的 ID 类型是 `UniqueIdentifier = string | number`，整个项目实际只用 string，强转可接受。可以在调用 `useDroppable`/`useSortable` 时显式传 string，避免 `as` 断言。

### 4.3 `src/components/AiChatSidebar.tsx`

**P3 — 没有客户端长度限制提示**
后端 `validate_user_message` 限 2000 字符。前端 textarea 不限，超长会让用户提交后才发现错误。建议 `<textarea maxLength={2000}>` + 实时字数提示。

**P3 — Enter 不发送、Shift+Enter 不换行**
当前 textarea 的 Enter 是默认换行，Send 只能点按钮。可以加一个 Cmd/Ctrl+Enter 提交快捷键。UX 改进，非必须。

### 4.4 `src/components/KanbanCard.tsx`

**P2 — 编辑时点 Save 但 title 为空，无任何反馈**
`KanbanCard.tsx:51-53`：`if (!title.trim()) return` 静默不动作。用户会以为 Save 没生效。改成 `setError` 或者直接禁用 Save 按钮。

**P3 — `useSortable` 的 listeners 覆盖整张卡片**
`KanbanCard.tsx:41-42`：`{...listeners}` 直接挂在 `<article>` 上，包括 Edit/Delete 按钮区域。`PointerSensor` 配 `distance: 6` 区分了点击和拖动，但严格说应该把拖动 handle 限制到一个明确区域。当前能用，UX 接受，标 P3。

### 4.5 `src/lib/kanban.ts`

**P3 — `createTimestamp` 与后端时间精度不一致**
`kanban.ts:190` 返回带毫秒的 `2026-01-01T00:00:00.000Z`，后端 `storage.utc_now()` 返回秒精度 `2026-01-01T00:00:00Z`。同一份 board 中可能混着两种格式。`validate_board` 不校验格式所以不会报错，但前端做时间排序/比较时会有歧义。建议两端统一为秒精度。

**OK-for-MVP — `createId` 用 `Math.random` + `Date.now()`**
`kanban.ts:184-188`：碰撞概率极低、单人本地无所谓。后续 v0.3 多用户场景可以换 `crypto.randomUUID()`。

### 4.6 前端测试

**P3 — `KanbanBoard.test.tsx` 测试名称与行为脱节**
`KanbanBoard.test.tsx:53` 测试名为 `renames a column`，但只验证了 input value 与 fetch 被调用，没验证最终持久化的 board 内容。够用，可以更严。

**P3 — Playwright `moves a card between columns` 用绝对像素拖动**
`kanban.spec.ts:189-212` 用 `page.mouse.move/down/up` 模拟拖动。响应式布局变化会让坐标失效。可以考虑封装成 helper 或用 `dragTo`。当前能跑通，未坏不修。

---

## 5. 基础设施审查

### 5.1 `Dockerfile`

**P2 — 容器以 root 运行**
`Dockerfile` 整体没有 `USER` 指令。本地 demo 影响有限，但是个标准最佳实践，加两行就解决：

```dockerfile
RUN useradd --create-home --uid 10001 app
USER app
```

注意 `/app/data` 卷的所有者要匹配。

**P3 — 没有 `HEALTHCHECK`**
增加 `HEALTHCHECK CMD curl -f http://localhost:8000/api/health || exit 1` 能让编排系统知道容器是否就绪。MVP 不重要，部署时再加。

**P3 — `python:3.14-slim-bookworm` 是较新的镜像**
`pyproject.toml` 要求 `>=3.10`，Docker 锁定 3.14 没问题。值得在 `docs/RUNNING.md` 里注明 Python 版本基线。

### 5.2 `scripts/start-*.sh` / `start-*.ps1`

**P2 — 启动脚本不等待容器就绪**
所有平台脚本都是 `docker run -d` 后立即 `printf 'Server running at...'`。但 uvicorn 启动通常需要 1-3 秒，用户照着提示打开浏览器可能命中 connection refused。

```sh
docker run -d ...
for i in {1..30}; do
  curl -fsS "http://localhost:${PORT}/api/health" >/dev/null && break
  sleep 0.5
done
printf 'Server running at http://localhost:%s\n' "$PORT"
```

**P3 — `start-mac.sh` 与 `start-linux.sh` 内容完全相同**
两份脚本字节级一致。可以合并成一个 `start-unix.sh` + 系统检测，或者保留两份但加注释「intentionally identical, kept separate for discoverability」。

**P3 — 启动脚本都重新 `docker build`**
首次 build 后续启动也会重 build（虽然有 layer cache 很快）。可以加 `--no-cache=false` 默认行为或 `if image exists then skip build`，但 MVP 接受。

### 5.3 `.dockerignore`

`.git`、`.venv`、`node_modules`、`.env`、`data/` 都在。**正确**——确保 `.env` 不会被 COPY 进镜像，避免泄漏。

---

## 6. 文档与项目管理审查

**优点**：

- `docs/` 中英对照齐全（PLAN/ACCEPTANCE/RUNNING）。
- `AGENTS.md` 分层（root/backend/frontend/scripts），约束清晰。
- `docs/AUTH.md` 明确标注鉴权边界，是这个 MVP 最有价值的文档之一。
- `strategy/` 把长期方向与执行计划分开，避免污染 `docs/`。

**P3 — 项目根没有 `README.md`**
新人 clone 下来第一眼看不到「这是什么 / 怎么跑」。`frontend/README.md` 是 NextJS 模板留下的（只有 `npm run dev`，与项目 Docker 优先的运行方式不匹配）。建议加一份 8-15 行的根 `README.md`，引向 `docs/RUNNING.md`。

**P3 — `frontend/README.md` 存在但内容过时**
只写了 `npm run dev`，没提它需要后端 `/api/board`。建议要么删掉，要么改为指向项目根 `README.md`/`docs/RUNNING.md`。

**P3 — `docs/PLAN.md` 阶段 1 仍有未勾选 checkbox**
`PLAN.md:36-58` Phase 1 的 7 个 checkbox 全部 `[ ]`，但项目实际已经走完。是历史保留还是待办？建议要么补勾，要么显式标注「Phase 1 was retroactively documented」。

---

## 7. 安全审查

| 检查项 | 状态 |
|---|---|
| SQL 注入 | 安全。所有 query 都参数化（`storage.py`）。 |
| XSS | 安全。React 默认转义，无 `dangerouslySetInnerHTML`。 |
| CSRF | 不适用（MVP 无真实鉴权）。下一阶段加真实登录时必须考虑。 |
| 密钥泄漏 | 安全。`.env` 在 `.gitignore` 与 `.dockerignore` 中；`DEEPSEEK_API_KEY` 不在日志中输出。 |
| 错误信息泄漏 | 良好。`DeepSeekAPIError` 只暴露 HTTP 状态码，不带响应体。 |
| 输入限制 | 部分。用户消息/历史有上限；AI 返回与 board JSON 体积无上限（详见 P3 上限保护）。 |
| 路径穿越 | 不适用。无文件上传/下载路径参数。 |
| CORS | 不适用（同源静态服务）。 |

总体良好。**进入 v0.3 真实多用户前必须解决**的安全工作：

1. 后端会话/token 鉴权与 per-user 隔离（`docs/AUTH.md` 已规划）。
2. CSRF token（cookie 鉴权时）。
3. 密码哈希（argon2id 优先）或 OIDC。
4. 速率限制（AI 接口）。

---

## 8. 性能与可靠性审查

**P1 — DeepSeek 同步阻塞**（已在 §3.4 详述）

**P2 — 全板 PUT，无差量更新**
任何小改动都把整个 board JSON 通过 PUT 发回，并整体替换 SQLite 中的 `boards.data`。MVP 8 张卡可忽略，到 100+ 张卡时单次请求 payload 与序列化成本明显。差量协议是 v0.3 之后的工作。

**P2 — 前端列重命名无去抖**（已在 §4.2 详述）

**P3 — `KanbanBoard` 是单一大组件**
所有列的渲染、所有卡片、所有事件都在同一个组件树。React 16+ 自动比较开销低，但用 React DevTools 看的话每次按键都会重渲整板。`KanbanColumn` 没有 `React.memo`。MVP 可接受。

---

## 9. 优先级总结

| 等级 | 项目 | 文件:行 |
|---|---|---|
| **P1** | DeepSeek 客户端改异步，避免阻塞 FastAPI 线程池 | `deepseek.py:79`、`main.py:62` |
| **P1** | 列重命名加 debounce，每键一次 PUT 不可接受 | `KanbanBoard.tsx:151`、`KanbanColumn.tsx:48` |
| P2 | `DEEPSEEK_API_KEY` 缺失返回 503 而非 400 | `main.py:102,111` |
| P2 | `assistantMessage`/`operationSummary` 加 2000 字上限 | `ai.py:104-117` |
| P2 | `get_or_create_board` 用 `INSERT ... ON CONFLICT DO NOTHING` 处理并发 | `storage.py:216-222` |
| P2 | 多次 `updateBoard` 串行化或加版本号防丢更新 | `KanbanBoard.tsx:116-131` |
| P2 | `getChangedCardIds` 同时识别删除与列改名 | `KanbanBoard.tsx:36-57` |
| P2 | 编辑卡片标题为空时显式反馈 | `KanbanCard.tsx:51-53` |
| P2 | Docker 容器以非 root 用户运行 | `Dockerfile` |
| P2 | 启动脚本等 `/api/health` 就绪后再打印 URL | `scripts/start-*.sh/.ps1` |
| P3 | 引入 Pydantic 模型替换 `dict[str, Any]` body | `main.py:56,63` |
| P3 | `validate_board` 加体积/字符串长度上限 | `storage.py:121-179` |
| P3 | `read_root_env_value` 改用 `python-dotenv` | `deepseek.py:25-40` |
| P3 | 增加 `validate_board` 的直接单元测试参数化覆盖 | `backend/tests/` |
| P3 | 客户端 textarea `maxLength={2000}` + 字数提示 | `AiChatSidebar.tsx:78-84` |
| P3 | 前后端时间戳精度对齐 | `kanban.ts:190` ↔ `storage.py:16-19` |
| P3 | `loadBoard` 失败状态独立于 `saveStatus` | `KanbanBoard.tsx:62,89` |
| P3 | 加项目根 `README.md`，删/改过时的 `frontend/README.md` | 项目根 |
| P3 | `Dockerfile` 加 `HEALTHCHECK` | `Dockerfile` |
| P3 | `start-mac.sh` 与 `start-linux.sh` 合并或加注释 | `scripts/` |

---

## 10. 明确「不建议在 MVP 改」的项目

为避免误把 MVP 妥协当问题修，下列已在 `AGENTS.md`/`docs/` 中标注或经过权衡，**不建议现在动**：

1. **硬编码登录** — `docs/AUTH.md` 已声明边界，v0.3 统一替换。
2. **Board 整存整取的 JSON 模型** — `strategy/PRODUCT_EVOLUTION.zh.md` §"第四阶段" 已规划逐步拆分。
3. **AI 直接修改 board 而非「计划-确认-执行」** — `strategy/PRODUCT_EVOLUTION.zh.md` §"第二阶段" 已规划。
4. **没有审计日志/活动记录** — v0.2 工作。
5. **前后端默认 board 数据重复** — 已在 `CLAUDE.md` 标注，前端的 `initialData` 仅测试用，可在 v0.2 顺手清理。
6. **`createId` 用 `Math.random`** — 单用户单浏览器无碰撞风险。

---

## 11. 总结

该 MVP 是一个**成熟度高、边界清晰**的 v0.1：

- 测试金字塔完整：单元 → 集成 → e2e。
- 文档分层得当，把「执行」（`docs/`）与「方向」（`strategy/`）分开。
- AI 路径有真实的可靠性边界，不止是「能跑」。
- 代码量克制，没有 over-engineering。

**进入 v0.2 之前最值得修的两件事**：

1. DeepSeek 客户端异步化（`deepseek.py` + `main.py`）。
2. 列重命名 debounce + 编辑保存的串行化（`KanbanBoard.tsx`）。

其余 P2/P3 项可以按 `strategy/VIBE_CODING_WORKFLOW.zh.md` 的迭代节奏，在对应版本计划里成组解决，不必在主分支零散提交。
