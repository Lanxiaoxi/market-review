"""
pytest 全局配置：
- 必须在导入 app 模块前强制 mock 数据源（避免打真实 Tushare 网络、消耗积分）
- 使用独立临时 SQLite（不污染开发库 api/data/app.db）
"""

import os
import tempfile

# ── 在导入任何 app.* 之前设置环境 ──
os.environ["TUSHARE_TOKEN"] = ""        # 强制 mock 数据源
os.environ["APP_ENV"] = "test"
os.environ["API_TOKEN"] = ""            # 默认免鉴权（鉴权测试单独设置）
_tmp_dir = tempfile.mkdtemp(prefix="market_review_tests_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{os.path.join(_tmp_dir, 'test.db')}"

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def _init_db():
    """每个测试前确保表结构存在（create_all + 迁移均幂等）"""
    from app.models.db import init_db

    await init_db()
    yield
