"""
charts 路由：期现对比数据对齐逻辑单测（不触网）
"""

import pytest
from fastapi import HTTPException

from app.routers.charts import _align_series, FUTURES_CONTRACTS


def test_futures_contracts_config():
    """三个中金所合约的现货指数映射完整"""
    assert FUTURES_CONTRACTS["IF"]["spot"] == "000300.SH"
    assert FUTURES_CONTRACTS["IH"]["spot"] == "000016.SH"
    assert FUTURES_CONTRACTS["IM"]["spot"] == "000852.SH"
    assert FUTURES_CONTRACTS["IF"]["name"] == "沪深300"
    assert FUTURES_CONTRACTS["IH"]["name"] == "上证50"
    assert FUTURES_CONTRACTS["IM"]["name"] == "中证1000"


def test_unknown_contract_rejected():
    """未知合约应被拒绝（422）"""
    from app.routers.charts import get_futures_basis

    async def _call():
        await get_futures_basis(contract="XX")

    # get_futures_basis 是 async，用 asyncio 验证 raise
    import asyncio

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_call())
    assert exc.value.status_code == 422


def test_align_series_intersection():
    """按现货日期为主、期货缺失日跳过对齐"""
    spot = [
        {"date": "2026-08-26", "close": 4610.0},
        {"date": "2026-08-27", "close": 4620.0},
        {"date": "2026-08-28", "close": 4609.18},
    ]
    fut = [
        {"date": "2026-08-26", "close": 4625.0},
        {"date": "2026-08-28", "close": 4630.0},  # 08-27 期货缺失
    ]
    dates, spot_out, fut_out = _align_series(spot, fut)
    assert dates == ["2026-08-26", "2026-08-28"]
    assert spot_out == [4610.0, 4609.18]
    assert fut_out == [4625.0, 4630.0]


def test_align_series_empty_futures():
    """期货完全缺失 → 空结果（上层会 502）"""
    spot = [{"date": "2026-08-26", "close": 4610.0}]
    dates, spot_out, fut_out = _align_series(spot, [])
    assert dates == []
    assert spot_out == []
    assert fut_out == []
