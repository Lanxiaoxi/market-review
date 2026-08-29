"""
历史快照测试：同日 upsert、按日期查询
"""

import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.main import app
from app.config import SHANGHAI_TZ
from app.models.db import async_session
from app.models.snapshot import DailySnapshot

transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_snapshot_upsert_and_query():
    today = datetime.datetime.now(SHANGHAI_TZ).date().isoformat()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 同日两次快照：不报错（第二次为覆盖更新）
        first = await client.post("/api/history/snapshot")
        assert first.status_code == 200, first.text
        second = await client.post("/api/history/snapshot")
        assert second.status_code == 200, second.text

        # 库中该日只有一行
        async with async_session() as session:
            stmt = select(DailySnapshot).where(DailySnapshot.snapshot_date == today)
            rows = (await session.execute(stmt)).scalars().all()
            assert len(rows) == 1

        # 按日期查询
        resp = await client.get("/api/history", params={"date": today})
        assert resp.status_code == 200
        body = resp.json()
        assert body["date"] == today
        assert len(body["indices"]) == 10


@pytest.mark.asyncio
async def test_history_missing_404():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/history", params={"date": "1999-01-01"})
        assert resp.status_code == 404
