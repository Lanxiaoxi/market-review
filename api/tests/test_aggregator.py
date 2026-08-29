"""
aggregator 单测 + 接口冒烟（mock 数据源）
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.overview import OverviewOut


@pytest.mark.asyncio
async def test_overview_schema():
    """聚合器返回合法 OverviewOut"""
    from app.services.aggregator import build_overview

    data = await build_overview()
    assert isinstance(data, OverviewOut)
    assert len(data.indices) == 10
    assert data.breadth.up > 0
    assert len(data.sectors_up) == 5
    assert len(data.sectors_down) == 5


@pytest.mark.asyncio
async def test_overview_limit_counts_match_dist():
    """涨停/跌停家数必须来自分布桶真实统计（而非 TOP5 列表长度）"""
    from app.services.aggregator import build_overview

    data = await build_overview()
    # mock 数据源：涨停 48 / 跌停 6
    assert data.breadth.limit_up_count == 48
    assert data.breadth.limit_down_count == 6
    assert len(data.breadth.limit_up_top) == 5
    # 7 档分布且与涨跌家数自洽
    dist = {d.label: d.value for d in data.breadth.dist}
    assert len(dist) == 7
    assert dist["涨停"] == data.breadth.limit_up_count
    assert dist["跌停"] == data.breadth.limit_down_count
    assert dist["涨停"] + dist["涨2-10%"] + dist["涨0-2%"] == data.breadth.up
    assert dist["跌停"] + dist["跌2-10%"] + dist["跌0-2%"] == data.breadth.down


@pytest.mark.asyncio
async def test_overview_date_is_valid():
    """overview.date 必须是合法 ISO 日期，且与 weekday 对应"""
    from app.services.aggregator import build_overview

    data = await build_overview()
    assert data.date.count("-") == 2
    assert data.weekday in {"周一", "周二", "周三", "周四", "周五", "周六", "周日"}


@pytest.mark.asyncio
async def test_overview_endpoint():
    """GET /api/overview 冒烟"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/overview")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["indices"]) == 10
        assert body["breadth"]["limitUpCount"] == 48


@pytest.mark.asyncio
async def test_overview_etag_304():
    """ETag 条件请求：二次请求带 If-None-Match 应返回 304"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/overview")
        assert first.status_code == 200
        etag = first.headers.get("etag")
        assert etag and etag.startswith('W/"')

        second = await client.get("/api/overview", headers={"If-None-Match": etag})
        assert second.status_code == 304
        # 数据未变，ETag 应稳定
        third = await client.get("/api/overview")
        assert third.headers.get("etag") == etag


@pytest.mark.asyncio
async def test_sectors_endpoint():
    """GET /api/sectors 冒烟"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sectors")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 10


@pytest.mark.asyncio
async def test_sectors_sort():
    """sectors 排序：pct 降序 / pct-asc 升序"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        desc = (await client.get("/api/sectors?sort=pct")).json()
        asc = (await client.get("/api/sectors?sort=pct-asc")).json()
        desc_pcts = [s["pct"] for s in desc]
        asc_pcts = [s["pct"] for s in asc]
        assert desc_pcts == sorted(desc_pcts, reverse=True)
        assert asc_pcts == sorted(asc_pcts)


@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /api/health"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
