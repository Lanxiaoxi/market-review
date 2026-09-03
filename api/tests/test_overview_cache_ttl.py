"""
overview 内存缓存 TTL 的选择逻辑：只有「数据真定格」才允许长缓存。

背景：store.is_settled 只看挂钟时间（15:05 后即视为已定格），而数据源
（Tushare 日线）要到 18:00 前后才更新当日数据。若单凭 is_settled 判定，
15:05~18:00 之间就会把盘中半日数据按 24h 缓存锁死。因此以「本地 L2 是否
已有该交易日数据」为最终依据。
"""

from datetime import date

import time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.cache import DEFAULT_TTL, INTRADAY_TTL, overview_cache
from app.main import app
from app.routers.overview import _resolve_ttl
from app.services import store
from tests.fake_data import BREADTH as FAKE_BREADTH

_TODAY = date(2026, 9, 3)


def _patch_today(monkeypatch, today=_TODAY):
    monkeypatch.setattr(store, "today_shanghai", lambda: today)


def _patch_l2(monkeypatch, has_data: bool):
    async def _read_breadth(session, trade_date):
        return {"up": 1, "down": 1} if has_data else None

    monkeypatch.setattr(store, "read_breadth", _read_breadth)


@pytest.mark.asyncio
async def test_past_trade_date_uses_long_ttl(session: AsyncSession, monkeypatch):
    """历史交易日已定格，直接长缓存（不额外查库）"""
    _patch_today(monkeypatch)
    assert await _resolve_ttl(session, "2026-09-02") == DEFAULT_TTL


@pytest.mark.asyncio
async def test_today_settled_and_persisted_uses_long_ttl(
    session: AsyncSession, monkeypatch
):
    """当日数据已落 L2 → 不会再变，长缓存"""
    _patch_today(monkeypatch)
    monkeypatch.setattr(store, "is_settled", lambda d, now=None: True)
    _patch_l2(monkeypatch, has_data=True)
    assert await _resolve_ttl(session, "2026-09-03") == DEFAULT_TTL


@pytest.mark.asyncio
async def test_today_settled_but_not_persisted_uses_short_ttl(
    session: AsyncSession, monkeypatch
):
    """已过收盘钟点但 L2 尚未回填（15:05~18:00 窗口）→ 短缓存，等数据到"""
    _patch_today(monkeypatch)
    monkeypatch.setattr(store, "is_settled", lambda d, now=None: True)
    _patch_l2(monkeypatch, has_data=False)
    assert await _resolve_ttl(session, "2026-09-03") == INTRADAY_TTL


@pytest.mark.asyncio
async def test_intraday_uses_short_ttl(session: AsyncSession, monkeypatch):
    """盘中：即便 L2 有昨天的数据，当日未定格也只短缓存"""
    _patch_today(monkeypatch)
    monkeypatch.setattr(store, "is_settled", lambda d, now=None: False)
    _patch_l2(monkeypatch, has_data=True)
    assert await _resolve_ttl(session, "2026-09-03") == INTRADAY_TTL


@pytest.mark.asyncio
async def test_invalid_date_falls_back_to_short_ttl(
    session: AsyncSession, monkeypatch
):
    """日期字段异常时不猜，按最短 TTL 处理"""
    _patch_today(monkeypatch)
    assert await _resolve_ttl(session, "not-a-date") == INTRADAY_TTL


# ── 端到端：走真实端点，看缓存里实际写入的 TTL ──


def _l2_breadth(trade_date: date) -> dict:
    """构造一条合法的 L2 breadth 记录（同构于 store.read_breadth 的返回）"""
    row = dict(FAKE_BREADTH)
    row["trade_date"] = trade_date.isoformat()
    row["turnover_yi"] = 1.26
    return row


async def _get_overview() -> int:
    """请求一次 /api/overview，返回 200 时缓存条目剩余秒数"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/overview")
        assert r.status_code == 200, r.text[:200]
    entry = overview_cache._store.get("overview")
    assert entry is not None, "overview 未写入缓存"
    return entry[0] - time.time()


@pytest.mark.asyncio
async def test_endpoint_short_ttl_when_l2_empty(monkeypatch):
    """15:05~18:00 窗口：挂钟已定格但 L2 未回填 → 端点只写 60s 缓存"""
    monkeypatch.setattr(store, "today_shanghai", date.today)
    monkeypatch.setattr(store, "is_settled", lambda d, now=None: True)

    async def _empty(session, trade_date):
        return None

    monkeypatch.setattr(store, "read_breadth", _empty)

    remain = await _get_overview()
    assert remain <= INTRADAY_TTL + 5, f"应走 60s 短缓存，实际剩余 {remain:.0f}s"


@pytest.mark.asyncio
async def test_endpoint_long_ttl_when_l2_persisted(monkeypatch):
    """当日数据已落 L2 → 端点写 24h 缓存"""
    monkeypatch.setattr(store, "today_shanghai", date.today)
    monkeypatch.setattr(store, "is_settled", lambda d, now=None: True)

    async def _filled(session, trade_date):
        return _l2_breadth(trade_date)

    monkeypatch.setattr(store, "read_breadth", _filled)

    remain = await _get_overview()
    assert remain > DEFAULT_TTL - 120, f"应走 24h 长缓存，实际剩余 {remain:.0f}s"
