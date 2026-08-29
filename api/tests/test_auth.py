"""
可选 API Token 鉴权测试：配置 API_TOKEN 后写接口需携带 X-API-Token
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.config import get_settings

transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_api_token_required_when_configured(monkeypatch):
    # 先清缓存，再注入 API_TOKEN（Settings 惰性读取 + lru_cache）
    get_settings.cache_clear()
    monkeypatch.setenv("API_TOKEN", "test-secret")
    get_settings.cache_clear()
    assert get_settings().has_api_token

    code = "600004.SH"
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 无 token → 401
            no_token = await client.post("/api/watchlist", json={"code": code, "name": "X"})
            assert no_token.status_code == 401
            # 错误 token → 401
            bad = await client.post(
                "/api/watchlist", json={"code": code, "name": "X"},
                headers={"X-API-Token": "wrong"},
            )
            assert bad.status_code == 401
            # 正确 token → 201
            ok = await client.post(
                "/api/watchlist", json={"code": code, "name": "X"},
                headers={"X-API-Token": "test-secret"},
            )
            assert ok.status_code == 201, ok.text
            # 读接口不受限
            listed = await client.get("/api/watchlist")
            assert listed.status_code == 200
    finally:
        # 恢复：清缓存 + 还原环境（读接口 DELETE 需 token，直接用会话带 token 清理）
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.delete(
                f"/api/watchlist/{code}", headers={"X-API-Token": "test-secret"}
            )
        monkeypatch.delenv("API_TOKEN", raising=False)
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_no_token_configured_means_open():
    """默认（未配置 API_TOKEN）写接口免鉴权"""
    get_settings.cache_clear()
    code = "600005.SH"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            resp = await client.post("/api/watchlist", json={"code": code, "name": "Y"})
            assert resp.status_code == 201, resp.text
        finally:
            await client.delete(f"/api/watchlist/{code}")
