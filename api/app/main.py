"""FastAPI 应用入口：实例化 + 路由注册 + CORS + 日志"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.db import init_db
from app.routers import overview, sectors, watchlist, charts, history, intraday
from app.tasks import start_scheduler, shutdown_scheduler

# 统一日志（模块内用 logging.getLogger(__name__)）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化 DB（含轻量迁移）+ 图表库种子 + 定时任务
    await init_db()
    from app.models.db import async_session
    from app.services.chart_library import seed_chart_library

    async with async_session() as session:
        await seed_chart_library(session)
    start_scheduler()
    yield
    # 关闭
    shutdown_scheduler()


app = FastAPI(
    title="收盘复盘仪表盘 API",
    version="0.0.2",
    lifespan=lifespan,
)

settings = get_settings()

# CORS：开发环境放开所有来源；生产用 CORS_ORIGINS 白名单（逗号分隔）。
# 注意：不使用 allow_credentials（与 allow_origins=* 组合违反 CORS 规范），
# 实际部署走 Caddy/Vite 同域代理，本配置仅兜底开发直连场景。
if settings.is_dev:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

# 注册路由
app.include_router(overview.router, prefix="/api")
app.include_router(sectors.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(charts.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(intraday.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
