"""SQLModel 数据库引擎与 session 初始化（含轻量迁移）"""

import logging

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings, DATA_DIR

logger = logging.getLogger(__name__)

settings = get_settings()

# 确保 data 目录存在（SQLite 无法自动创建目录）
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 异步 SQLite 引擎
engine = create_async_engine(
    settings.database_url,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _run_migrations(sync_conn) -> None:
    """轻量迁移：create_all 不会为已有表补列/索引，这里手工补齐。

    约定：所有迁移必须幂等（IF NOT EXISTS / 列存在性检查），
    后续 schema 变更在此追加即可（正式多实例部署再引入 alembic）。
    """
    # 0.0.2: watchlist.cost 成本价列（持仓盈亏计算）
    cols = {row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(watchlist)")}
    if "cost" not in cols:
        sync_conn.exec_driver_sql("ALTER TABLE watchlist ADD COLUMN cost REAL DEFAULT 0")
        logger.info("[migrate] watchlist 增加 cost 列")

    # 0.0.2: watchlist.code 唯一索引（防重复自选）
    try:
        sync_conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_watchlist_code ON watchlist (code)"
        )
    except Exception as e:  # 历史数据已存在重复 code 时索引创建失败
        logger.warning("[migrate] 创建 watchlist.code 唯一索引失败（存在重复数据？）: %s", e)


async def init_db():
    """创建所有表 + 轻量迁移（启动时执行）"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.run_sync(_run_migrations)


async def get_session() -> AsyncSession:
    """FastAPI 依赖注入：获取异步 session"""
    async with async_session() as session:
        yield session