# Vibe Coding 版本迭代工作流

这份文档记录 MVP 之后如何继续使用 vibe coding 模式进行版本更新。目标是保持开发速度，同时避免需求、实现、测试和文档混在一起失控。

## 基本原则

每个版本都应遵循：

```text
确定版本目标
-> 新建 git 分支
-> 起草版本计划
-> 审查并批准计划
-> 分阶段实现
-> 每阶段测试
-> 手动验收
-> 更新计划勾选
-> 提交 git
-> 进入下一阶段
```

不要直接跳到写代码。这个项目的 MVP 能稳定完成，关键原因就是计划、实现、验证和提交是分开的。

## Git 分支

MVP 最终版已经提交后，新功能应从新分支开始：

```sh
git checkout -b v0.2-product-basics
```

建议每个版本一个主分支：

```text
v0.2-product-basics
v0.3-real-auth
v0.4-ai-workflow
```

这样 MVP 主线始终是稳定锚点。如果某个版本探索失败，可以直接放弃分支，不影响已完成版本。

## AGENTS.md

不要重写根目录 `AGENTS.md`。它应该像项目宪法一样保持稳定。

可以轻微扩写，加入版本迭代规则，例如：

```md
## Iteration Workflow

After the MVP, each product version should have its own plan in `docs/`.
Do not start implementation until the version plan is reviewed and approved.
Keep changes scoped to the active version.
Update the version plan as phases are completed.
```

只有当项目的长期规则变化时，才修改 `AGENTS.md`。

## 版本计划文档

不要覆盖旧的 MVP `docs/PLAN.md` 和 `docs/PLAN.zh.md`。它们是 MVP 的历史记录。

每个新版本新建自己的计划：

```text
docs/PLAN.v0.2.md
docs/PLAN.v0.2.zh.md
```

计划建议包含：

- 当前版本目标。
- 范围内功能。
- 明确不做什么。
- 阶段拆分。
- 每阶段任务。
- 每阶段测试。
- 成功标准。
- 需要用户批准的节点。

## 推荐协作方式

### 1. 起草计划

可以这样发起：

```text
请基于当前 MVP，为 v0.2 Product Basics 起草英文和中文计划，不要写代码。
```

这一步只做规划，不修改功能代码。

### 2. 审查计划

检查计划是否过大、是否符合当前版本目标、是否遗漏验收标准。

如果计划需要调整，先改计划，不急着实现。

### 3. 批准执行

计划确认后再开始：

```text
我批准 v0.2 计划，请从 Phase 1 开始执行。
```

### 4. 分阶段推进

每个 phase 完成后应做：

- 运行对应自动化测试。
- 如有需要，运行 Docker 或浏览器验收。
- 更新 `PLAN.v0.2.md` 和 `PLAN.v0.2.zh.md` 的勾选状态。
- 总结改动和验证结果。
- 用户确认后提交 git。

## 提交节奏

推荐提交粒度：

- 一个 phase 一个 commit。
- 文档计划更新可以和对应 phase 一起提交。
- 大型重构单独提交。
- 修复测试失败单独提交。

提交前建议检查：

```sh
git status --short
git diff --check
```

根据变更范围运行：

```sh
cd backend
../.venv/bin/uv run --extra dev pytest
cd ..
```

```sh
cd frontend
npm run lint
npm run test:unit
npm run test:e2e
npm run build
cd ..
```

## 文档结构建议

推荐保留：

```text
docs/
  PLAN.md
  PLAN.zh.md
  PLAN.v0.2.md
  PLAN.v0.2.zh.md
  ACCEPTANCE.md
  ACCEPTANCE.zh.md
  AI.md
  AUTH.md
  DATABASE.md
  RUNNING.md
  RUNNING.zh.md

strategy/
  PRODUCT_EVOLUTION.zh.md
  VIBE_CODING_WORKFLOW.zh.md
```

其中：

- `docs/` 放执行型文档和具体技术说明。
- `strategy/` 放长期方向和工作方法。

## 每个版本的完成标准

一个版本完成前，至少应满足：

- 版本计划所有成功标准已打勾。
- 自动化测试通过。
- 手动验收通过。
- 文档已更新。
- 没有遗留后台 Docker 容器。
- 没有泄露 `.env` 或密钥。
- git 工作区只包含本版本应提交的内容。

## 常见风险

### 功能越加越散

解决方式：每个版本只服务一个明确目标。超出范围的想法先记下，不立刻做。

### AI 一次改太多

解决方式：让 AI 先写计划，用户批准后再执行。实现时按 phase 切小。

### 文档和代码不同步

解决方式：每个 phase 完成时立刻更新计划和相关文档。

### 测试推迟到最后

解决方式：每个 phase 都有自己的测试和成功标准，不把验证堆到版本末尾。

### Git 变更太大

解决方式：每个 phase 提交一次，提交前看 `git diff --stat`。

## 推荐下一步

当前最自然的下一步是：

```sh
git checkout -b v0.2-product-basics
```

然后起草：

```text
docs/PLAN.v0.2.md
docs/PLAN.v0.2.zh.md
```

等计划批准后，再开始 v0.2 的第一阶段实现。
