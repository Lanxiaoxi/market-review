"""
pytest 全局配置：
- 必须在导入 app 模块前强制 mock 数据源（避免打真实 Tushare 网络、消耗积分）
- 使用独立临时 SQLite（不污染开发库 api/data/app.db）
"""

import os
import tempfile

# ── 在导入任何 app.* 之前设置环境 ──
os.environ["TUSHARE_TOKEN"] = ""        # 强制 mock 数据源
os.environ["THS_API_KEY"] = ""          # 同花顺数据源同样禁用（不触网）
os.environ["APP_ENV"] = "test"
os.environ["API_TOKEN"] = ""            # 默认免鉴权（鉴权测试单独设置）
_tmp_dir = tempfile.mkdtemp(prefix="market_review_tests_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{os.path.join(_tmp_dir, 'test.db')}"

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def _fake_data_sources(monkeypatch):
    """生产已无 mock 数据：测试注入确定性数据源（patch aggregator.fetch_domain）"""
    import app.services.aggregator as aggregator
    from tests.fake_data import fake_fetch_domain

    monkeypatch.setattr(aggregator, "fetch_domain", fake_fetch_domain)
    yield


@pytest_asyncio.fixture(autouse=True)
async def _init_db():
    """每个测试前：确保表结构存在 + 清空数据 + 清空内存缓存

    用例之间完全隔离，避免依赖执行顺序（此前 watchlist 类测试就隐式依赖空库）。
    """
    from sqlmodel import SQLModel

    from app.cache import clear_all
    from app.models.db import engine, init_db

    await init_db()
    async with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(table.delete())
    clear_all()
    yield


@pytest_asyncio.fixture
async def session():
    """一个干净的 session（数据清理由 _init_db 统一负责）"""
    from app.models.db import async_session

    async with async_session() as s:
        yield s
