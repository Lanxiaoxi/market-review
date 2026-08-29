"""
provider 注册表与映射表单测（不触网）
"""

import pytest

# 注册 SQLModel 表（否则 create_all 建空库，init_db 迁移报错）
from app.models import watchlist, chart_config, snapshot  # noqa: F401

from app.services import provider
from app.services.provider import (
    BaseProvider,
    ProviderError,
    CAPABILITY,
    DOMAIN_PROVIDER,
    DOMAINS,
    fetch_domain,
    get_provider,
    _resolve_chain,
)


def test_mapping_config_valid():
    """映射表每个域的主源必须属于该域能力矩阵"""
    for domain in DOMAINS:
        assert DOMAIN_PROVIDER[domain] in CAPABILITY[domain], (
            f"{domain} 主源 {DOMAIN_PROVIDER[domain]} 不在能力矩阵 {CAPABILITY[domain]}"
        )


def test_resolve_chain_order():
    """降级链 = 配置主源 + 能力矩阵中排在它后面的候选"""
    assert _resolve_chain("sectors") == ["ths", "tushare"]
    assert _resolve_chain("indices") == ["tushare", "ths"]
    assert _resolve_chain("limit_up") == ["ths", "tushare"]
    assert _resolve_chain("intraday") == ["tencent"]


def test_get_provider_returns_configured_primary():
    """get_provider 返回配置的主源实例"""
    assert get_provider("sectors").name == "ths"
    assert get_provider("indices").name == "tushare"
    assert get_provider("intraday").name == "tencent"


def test_unknown_domain_raises():
    with pytest.raises(ProviderError):
        _resolve_chain("bogus")


@pytest.mark.asyncio
async def test_fetch_unknown_domain_raises():
    with pytest.raises(ProviderError):
        await fetch_domain("bogus")


@pytest.mark.asyncio
async def test_fetch_domain_falls_back_on_provider_failure():
    """主源失败时自动降级到下一个候选（sectors: ths 挂 → tushare mock）"""
    from app.services.ths_provider import ThsProvider
    from app.services.tushare_provider import TushareProvider

    async def _boom(self):
        raise ProviderError("模拟 THS 故障")

    provider._instances.clear()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(ThsProvider, "fetch_sectors", _boom)
    try:
        result = await fetch_domain("sectors")
        # 降级到 tushare（测试环境无 token → 内部 mock），应返回非空列表
        assert isinstance(result, list) and len(result) >= 5
    finally:
        monkeypatch.undo()
        provider._instances.clear()


@pytest.mark.asyncio
async def test_fetch_domain_all_providers_fail():
    """全部候选失败时 raise ProviderError"""
    from app.services.ths_provider import ThsProvider
    from app.services.tushare_provider import TushareProvider

    async def _boom(self):
        raise ProviderError("模拟故障")

    provider._instances.clear()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(ThsProvider, "fetch_sectors", _boom)
    monkeypatch.setattr(TushareProvider, "fetch_sectors", _boom)
    try:
        with pytest.raises(ProviderError):
            await fetch_domain("sectors")
    finally:
        monkeypatch.undo()
        provider._instances.clear()


@pytest.mark.asyncio
async def test_ths_provider_without_key_raises():
    """未配置 THS_API_KEY 时 ThsProvider 明确报错（供降级链捕获）"""
    from app.services.ths_provider import ThsProvider

    tp = ThsProvider()
    with pytest.raises(ProviderError):
        await tp.fetch_indices()


def test_base_provider_unsupported_domains_raise():
    """BaseProvider 未实现的域方法必须 raise（防误用）"""
    bp = BaseProvider()

    async def _call(method):
        with pytest.raises(ProviderError):
            await method

    import asyncio

    asyncio.run(_call(bp.fetch_sectors()))
    asyncio.run(_call(bp.fetch_intraday(["sh000001"])))
