"""
L2 命中验证：数据回填进本地库后，所有读接口必须零回源。

做法：回填完成后把各模块的 fetch_domain 换成「一调用就抛错」的探针，
再打接口 —— 只要还能返回 200 且数据正确，就证明请求没碰数据源。
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.cache import clear_all
from app.main import app
from app.services import backfill, store
from tests.fake_backfill import TRADE_DAYS, install

transport = ASGITransport(app=app)

# 持有 fetch_domain 引用的模块：全部替换才算彻底封死回源路径
_FETCH_DOMAIN_HOSTS = (
    "app.services.aggregator",
    "app.routers.charts",
    "app.routers.watchlist",
    "app.routers.intraday",
    "app.services.snapshot_service",
)


async def _boom(*args, **kwargs):
    raise AssertionError("命中 L2 后不应再回源调用数据源")


def _seal_providers(monkeypatch):
    import importlib

    for path in _FETCH_DOMAIN_HOSTS:
        mod = importlib.import_module(path)
        if hasattr(mod, "fetch_domain"):
            monkeypatch.setattr(mod, "fetch_domain", _boom)


async def _seed(session: AsyncSession, monkeypatch):
    install(monkeypatch)
    await store.sync_calendar(session, TRADE_DAYS)
    await backfill.backfill(session, days=5, intraday_codes=["sh000001"])
    return TRADE_DAYS[-1]


@pytest.mark.asyncio
async def test_overview_reads_from_l2(session: AsyncSession, monkeypatch):
    last_day = await _seed(session, monkeypatch)
    clear_all()
    _seal_providers(monkeypatch)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/overview")

    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == last_day.isoformat()
    assert body["breadth"]["limitUpCount"] == 2, "涨停家数应来自本地聚合"
    assert len(body["indices"]) == 4, "本地库有 4 只指数"
    assert len(body["sectorsUp"]) == 1


@pytest.mark.asyncio
async def test_sectors_reads_from_l2(session: AsyncSession, monkeypatch):
    await _seed(session, monkeypatch)
    clear_all()
    _seal_providers(monkeypatch)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sectors")

    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "半导体"


@pytest.mark.asyncio
async def test_limit_counts_reads_from_l2(session: AsyncSession, monkeypatch):
    """改造前该接口冷启动要打 2×days 次涨停池/跌停池，现在必须 0 次"""
    await _seed(session, monkeypatch)
    clear_all()
    _seal_providers(monkeypatch)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/charts/limit-counts?days=10")

    assert resp.status_code == 200
    body = resp.json()
    assert body["limitUp"] == [2] * 5, "本地只有 5 天，days=10 时返回全部 5 天"
    assert body["limitDown"] == [1] * 5


@pytest.mark.asyncio
async def test_futures_basis_reads_from_l2(session: AsyncSession, monkeypatch):
    await _seed(session, monkeypatch)
    clear_all()
    _seal_providers(monkeypatch)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/charts/futures-basis?contract=IF&days=10")

    assert resp.status_code == 200
    body = resp.json()
    assert body["contract"] == "IF"
    assert len(body["dates"]) == 5, "本地只有 5 天，days=10 时返回全部 5 天"


@pytest.mark.asyncio
async def test_intraday_reads_frozen_bars(session: AsyncSession, monkeypatch):
    await _seed(session, monkeypatch)
    clear_all()
    _seal_providers(monkeypatch)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/intraday?codes=sh000001")

    assert resp.status_code == 200
    series = resp.json()["codes"]["sh000001"]
    assert series["prices"] == [3200.0, 3201.0, 3202.0]


@pytest.mark.asyncio
async def test_watchlist_sparkline_reads_from_l2(session: AsyncSession, monkeypatch):
    """自选股 sparkline 命中本地 stock_daily，不再逐只打接口"""
    from app.models.watchlist import WatchlistItem

    await _seed(session, monkeypatch)
    session.add(
        WatchlistItem(code="600000", name="股票0", price=10.0, cost=9.0, change_pct=0.0,
                      pnl=0.0, holding_value=100.0, position_pct=10.0, sort_order=1)
    )
    await session.commit()

    clear_all()
    _seal_providers(monkeypatch)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/watchlist")

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items[0]["code"] == "600000"
    assert items[0]["sparkline"] == [14] * 5, "近 5 日收盘价归一化后应为常量序列"
