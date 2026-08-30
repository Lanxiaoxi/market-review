# AGENTS.md

面向在本仓库工作的 AI 智能体 / 协作者的约定。

## 1. 代码改动必须使用 Git 管理

- **改动前**：先 `git status` 与 `git diff` 查看当前工作区与未提交改动，避免误覆盖他人/之前的修改。
- **改动后**：用 `git diff` 复查本次改动，确认无调试残留、无意外文件（`node_modules/`、`dist/`、`*.tsbuildinfo`、本地数据文件等已在 `.gitignore` 中，不要手动提交）。
- **提交规范**：使用 Conventional Commits 风格，例如：
  - `feat(web): 市场宽度表格 v2 动效`
  - `fix(api): THS 兜底移除中证2000（932000）`
  - `refactor: 移除 mock 数据`
  - `docs: 补充部署说明`
- **提交粒度**：一个逻辑改动一个提交，不要把无关改动混在一起；提交前先 `git add` 对应文件。
- **不要**：不要提交密钥/Token（`.env` 已在 `.gitignore`，仅提交 `.env.example`）；不要提交构建产物。

## 2. 后端使用 uv 管理

- **环境**：Python 依赖统一用 [uv](https://docs.astral.sh/uv/) 管理（`api/pyproject.toml` + `api/uv.lock`），**不要直接 `pip install`**。
- **安装依赖**：在 `api/` 目录执行 `uv sync`（含开发依赖用 `uv sync --extra dev`）。
- **运行命令**：统一用 `uv run`，例如：
  - 启动后端：`uv run uvicorn app.main:app --reload --port 8000`
  - 跑测试：`uv run pytest`
- **新增依赖**：`uv add <包名>`（开发依赖用 `uv add --dev <包名>`），会同步更新 `uv.lock`。
- **锁文件**：`uv.lock` 是提交对象，依赖变更后必须一起提交，保证可复现。
- **不要**：不要手动编辑 `uv.lock`；不要绕过 uv 直接改 `.venv`。

## 附：前端环境（供参考）

前端 `web/` 用 npm 管理：`npm install` / `npm run dev` / `npm run build` / `npm run lint`，不涉及 uv。
