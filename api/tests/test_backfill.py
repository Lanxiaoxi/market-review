"""回填服务测试：缺口识别、幂等去重、分时固化"""

import datetime as dt

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services import backfill, provider, store
from tests.fake_backfill import TRADE_DAYS, install

LAST_DAY = TRADE_DAYS[-1]


async def _seed_calendar(session: AsyncSession):
    await store.sync_calendar(session, TRADE_DAYS)


@pytest.mark.asyncio
async def test_backfill_fills_all_domains(session: AsyncSession, monkeypatch):
    """首次回填应把各域数据写入本地库"""
    calls = install(monkeypatch)
    await _seed_calendar(session)

    stats = await backfill.backfill(session, days=5)

    assert stats["stock_daily"] == 5, "应回填 5 个交易日的个股日线"
    assert stats["index_daily"] == 5
    assert stats["sector_daily"] == 5
    assert stats["stock_names"] == 6
    assert stats["futures"] == 3 * len(TRADE_DAYS), "3 个合约 × 5 天"

    # 涨停家数序列：每天 2 只涨停 / 1 只跌停
    counts = await store.read_limit_counts(session, 5)
    assert len(counts) == 5
    assert all(c["limit_up"] == 2 and c["limit_down"] == 1 for c in counts)

    # 指数 / 板块 / 期货读回
    assert await store.read_indices(session, LAST_DAY) is not None
    assert await store.read_sectors(session, LAST_DAY) is not None
    assert len(await store.read_futures_series(session, "IF", 60)) == 5

    # 回源次数：日历 1 + 名称 1 + 个股日线 5 + 指数 1 + 板块 1 + 期货 3
    assert len(calls) == 12, f"首次回填回源次数异常: {calls}"


@pytest.mark.asyncio
async def test_backfill_is_idempotent(session: AsyncSession, monkeypatch):
    """重复运行不得产生任何回源（这是「避免重复获取数据」的核心断言）"""
    calls = install(monkeypatch)
    await _seed_calendar(session)

    await backfill.backfill(session, days=5)
    calls.clear()

    stats = await backfill.backfill(session, days=5)

    assert set(stats.values()) == {0}, f"二次回填不应有任何写入: {stats}"
    assert calls == [], f"二次回填不应触发任何回源: {calls}"


@pytest.mark.asyncio
async def test_backfill_only_fills_gaps(session: AsyncSession, monkeypatch):
    """已回填的日期被剔除后，只补缺口那一天"""
    calls = install(monkeypatch)
    await _seed_calendar(session)
    await backfill.backfill(session, days=5)

    # 人为抹掉中间一天的标记，模拟「某日回填失败」
    from sqlalchemy import delete as sa_delete

    from app.models.market_data import FetchLog

    gap_day = TRADE_DAYS[2]
    await session.execute(
        sa_delete(FetchLog).where(
            FetchLog.domain == provider.DOMAIN_STOCK_DAILY_RAW,
            FetchLog.ref_key == gap_day.isoformat(),
        )
    )
    await session.commit()

    calls.clear()
    stats = await backfill.backfill(session, days=5)

    assert stats["stock_daily"] == 1, f"只应补 1 天: {stats}"
    assert provider.DOMAIN_STOCK_DAILY_RAW in [c[0] for c in calls]
    daily_calls = [c for c in calls if c[0] == provider.DOMAIN_STOCK_DAILY_RAW]
    assert daily_calls[0][1][0] == gap_day, f"补的应是缺口日 {gap_day}: {daily_calls}"


@pytest.mark.asyncio
async def test_freeze_intraday(session: AsyncSession, monkeypatch):
    """收盘后固化分时，且同一天不重复固化"""
    calls = install(monkeypatch)
    await _seed_calendar(session)

    n = await backfill.freeze_intraday(session, LAST_DAY, ["sh000001"])
    assert n == 3, "3 个分钟点"

    bars = await store.read_intraday(session, LAST_DAY)
    assert bars["sh000001"]["prices"] == [3200.0, 3201.0, 3202.0]

    calls.clear()
    assert await backfill.freeze_intraday(session, LAST_DAY, ["sh000001"]) == 0
    assert calls == [], "同一交易日不应重复固化分时"


@pytest.mark.asyncio
async def test_backfill_endpoint(monkeypatch):
    """POST /api/history/backfill 手动触发回填，且重复调用返回全 0"""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    install(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/history/backfill?days=5")
        assert first.status_code == 200
        stats = first.json()
        assert stats["stock_daily"] > 0

        second = await client.post("/api/history/backfill?days=5")
        assert second.status_code == 200
        assert set(second.json().values()) == {0}, "重复触发不应再拉数据"


@pytest.mark.asyncio
async def test_is_settled():
    """定格判定：历史日恒为 True，当日取决于是否已过 15:05"""
    past = dt.date(2026, 8, 27)
    today = dt.date(2026, 8, 28)

    assert store.is_settled(past, dt.datetime(2026, 8, 28, 10, 0)) is True
    assert store.is_settled(today, dt.datetime(2026, 8, 28, 10, 0)) is False
    assert store.is_settled(today, dt.datetime(2026, 8, 28, 15, 5)) is True
    assert store.is_settled(dt.date(2026, 8, 29), dt.datetime(2026, 8, 28, 20, 0)) is False
