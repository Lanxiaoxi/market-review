"""SQLModel 数据库引擎与 session 初始化（含轻量迁移）"""

import logging

from sqlmodel import SQLModel
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings, DATA_DIR

# 注册表：所有 table=True 的模型必须先于 create_all 导入，否则表不会被创建。
# db.py 是 metadata 的拥有者，集中注册可避免「迁移依赖路由被导入」这类隐式顺序耦合。
from app.models import market_data, snapshot, watchlist  # noqa: F401

logger = logging.getLogger(__name__)

settings = get_settings()

# 确保 data 目录存在（SQLite 无法自动创建目录）
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 异步 SQLite 引擎
engine = create_async_engine(
    settings.database_url,
    echo=False,
)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """SQLite 写入优化：WAL + NORMAL 同步。

    回填单日全市场约 5400 行，同步模式为 FULL 时事务提交会明显拖慢。
    仅对 sqlite 连接生效，换 PostgreSQL 后自动跳过。
    """
    if type(dbapi_conn).__module__ != "aiosqlite.core" and "sqlite" not in str(type(dbapi_conn)):
        return
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA temp_store=MEMORY")
    cur.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# create_all 不会为已有表补索引，这里集中声明（全部 IF NOT EXISTS，幂等）
_EXTRA_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_stock_daily_date ON stock_daily (trade_date)",
    "CREATE INDEX IF NOT EXISTS ix_index_daily_date ON index_daily (trade_date)",
    "CREATE INDEX IF NOT EXISTS ix_sector_daily_date ON sector_daily (trade_date)",
    "CREATE INDEX IF NOT EXISTS ix_futures_daily_date ON futures_daily (trade_date)",
    "CREATE INDEX IF NOT EXISTS ix_intraday_bar_code_date ON intraday_bar (code, trade_date)",
    "CREATE INDEX IF NOT EXISTS ix_fetch_log_trade_date ON fetch_log (trade_date)",
    "CREATE INDEX IF NOT EXISTS ix_series_cache_expires ON series_cache (expires_at)",
)


def _table_exists(sync_conn, name: str) -> bool:
    row = sync_conn.exec_driver_sql(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _run_migrations(sync_conn) -> None:
    """轻量迁移：create_all 不会为已有表补列/索引，这里手工补齐。

    约定：所有迁移必须幂等（IF NOT EXISTS / 列存在性检查），
    后续 schema 变更在此追加即可（正式多实例部署再引入 alembic）。
    """
    # 0.0.2: watchlist.cost 成本价列（持仓盈亏计算）
    if _table_exists(sync_conn, "watchlist"):
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

    # 0.0.3: L2 行情持久层索引（按 trade_date 扫描是主查询模式）
    for ddl in _EXTRA_INDEXES:
        try:
            sync_conn.exec_driver_sql(ddl)
        except Exception as e:
            logger.warning("[migrate] 索引创建失败（表尚未建立？）: %s | %s", ddl, e)


async def init_db():
    """创建所有表 + 轻量迁移（启动时执行）"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.run_sync(_run_migrations)


async def get_session() -> AsyncSession:
    """FastAPI 依赖注入：获取异步 session"""
    async with async_session() as session:
        yield session