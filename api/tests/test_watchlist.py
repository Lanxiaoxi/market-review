"""
自选池 CRUD 接口测试（独立临时库 + mock 数据源）
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_watchlist_crud_roundtrip():
    code = "600000.SH"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            # 创建
            resp = await client.post("/api/watchlist", json={
                "code": code, "name": "浦发银行", "price": 10.5, "cost": 9.2,
                "holdingValue": 21.0, "positionPct": 12.5,
            })
            assert resp.status_code == 201, resp.text
            created = resp.json()
            assert created["cost"] == 9.2
            assert created["holdingValue"] == 21.0

            # 列表包含
            listed = (await client.get("/api/watchlist")).json()
            assert any(i["code"] == code for i in listed["items"])

            # 更新
            up = await client.put(f"/api/watchlist/{code}", json={"price": 11.0, "positionPct": 15.0})
            assert up.status_code == 200, up.text
            assert up.json()["price"] == 11.0
            assert up.json()["positionPct"] == 15.0

            # 删除
            dele = await client.delete(f"/api/watchlist/{code}")
            assert dele.status_code == 204
            after = (await client.get("/api/watchlist")).json()
            assert all(i["code"] != code for i in after["items"])
        finally:
            # 清理（失败时也保证不污染后续测试）
            await client.delete(f"/api/watchlist/{code}")


@pytest.mark.asyncio
async def test_watchlist_duplicate_409():
    code = "600001.SH"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            first = await client.post("/api/watchlist", json={"code": code, "name": "测试1"})
            assert first.status_code == 201, first.text
            dup = await client.post("/api/watchlist", json={"code": code, "name": "测试2"})
            assert dup.status_code == 409
        finally:
            await client.delete(f"/api/watchlist/{code}")


@pytest.mark.asyncio
async def test_watchlist_invalid_code_422():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/watchlist", json={"code": "abc", "name": "非法代码"})
        assert resp.status_code == 422
        resp2 = await client.post("/api/watchlist", json={"code": "600000", "name": "无后缀也可"})
        assert resp2.status_code == 201
        await client.delete("/api/watchlist/600000")


@pytest.mark.asyncio
async def test_watchlist_summary_math():
    """汇总公式：总市值=Σ市值、今日盈亏=Σpnl、持仓盈亏=Σ市值×(现价-成本)/现价、仓位=Σ仓位占比"""
    a, b = "600002.SH", "600003.SH"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            await client.post("/api/watchlist", json={
                "code": a, "name": "A", "price": 10.0, "cost": 8.0,
                "pnl": 1.0, "holdingValue": 50.0, "positionPct": 40.0,
            })
            await client.post("/api/watchlist", json={
                "code": b, "name": "B", "price": 20.0, "cost": 20.0,
                "pnl": -0.5, "holdingValue": 30.0, "positionPct": 30.0,
            })
            summary = (await client.get("/api/watchlist")).json()["summary"]
            # A: 50*(10-8)/10 = 10.0；B: 成本=现价 → 0
            assert summary["totalValue"] == pytest.approx(80.0)
            assert summary["todayPnl"] == pytest.approx(0.5)
            assert summary["holdingPnl"] == pytest.approx(10.0)
            assert summary["position"] == pytest.approx(70.0)
        finally:
            await client.delete(f"/api/watchlist/{a}")
            await client.delete(f"/api/watchlist/{b}")


@pytest.mark.asyncio
async def test_watchlist_update_missing_404():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put("/api/watchlist/999999.SH", json={"price": 1.0})
        assert resp.status_code == 404
        resp2 = await client.delete("/api/watchlist/999999.SH")
        assert resp2.status_code == 404
