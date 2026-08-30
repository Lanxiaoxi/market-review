# 前后端合并镜像（可选部署方式）
# 构建：docker build -t market-review .
# 运行：docker run -d -p 8668:8668 -v market-data:/app/api/data -e TUSHARE_TOKEN=xxx market-review

# ── 构建阶段：前端 ──
FROM node:20-alpine AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com
COPY web/ ./
RUN npm run build

# ── 构建阶段：后端 ──
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS api-build
WORKDIR /app/api
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen

# ── 运行阶段 ──
FROM python:3.12-slim
WORKDIR /app/api
COPY --from=api-build /app/api/.venv .venv
COPY api/ ./
COPY --from=web-build /build/web/dist /app/web/dist

EXPOSE 8668
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8668"]
