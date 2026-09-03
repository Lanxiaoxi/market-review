"""
腾讯分时/日 K 解析函数单测（无网络，纯解析）
"""

from app.services.tencent_provider import _parse_minute_rows, _parse_kline_rows


def test_parse_minute_rows():
    rows = [
        "0930 3950.24 4488109 8595747495.80",
        "0931 3952.78 17686048 34726850484.10",
        "0932 3956.84 29742433 59844577612.10",
    ]
    out = _parse_minute_rows(rows)
    assert out is not None
    assert out["times"] == ["09:30", "09:31", "09:32"]
    assert out["prices"] == [3950.24, 3952.78, 3956.84]
    assert out["amounts"] == [8595747495.80, 34726850484.10, 59844577612.10]


def test_parse_minute_rows_skips_bad_rows():
    rows = ["bad line", "0930 3950.24 4488109 8595747495.80"]
    out = _parse_minute_rows(rows)
    assert out is not None
    assert out["times"] == ["09:30"]


def test_parse_minute_rows_empty():
    assert _parse_minute_rows([]) is None
    assert _parse_minute_rows(["not-enough"]) is None


def test_parse_kline_rows():
    rows = [
        ["2026-08-13", "25288.070", "25396.510", "25519.390", "25288.070", "263710072490.000"],
        ["2026-08-14", "25219.150", "25116.850", "25311.860", "25089.140", "254179239620.000"],
    ]
    closes = _parse_kline_rows(rows)
    assert closes == [25396.51, 25116.85]


def test_parse_kline_rows_bad():
    assert _parse_kline_rows([["2026-08-13", "a", "b"]]) == []
    assert _parse_kline_rows([]) == []


# ── fetch_hk_index_range 的涨跌幅差分锚定 ────────────────────────────────

from datetime import date

import pytest

from app.services import tencent_provider


async def _fake_series(code, days):
    """模拟腾讯日 K：前一根（9/2）在区间外，后一根（9/3）为目标日"""
    return [
        (date(2026, 9, 1), 19900.0),
        (date(2026, 9, 2), 20000.0),
        (date(2026, 9, 3), 20100.0),
    ]


@pytest.fixture
def fake_kline(monkeypatch):
    monkeypatch.setattr(tencent_provider, "fetch_hk_kline_rows", _fake_series)


@pytest.mark.asyncio
async def test_hk_range_single_day_not_zero(fake_kline):
    """回归：单日区间（回填单日）时 prev 必须用区间外前一根锚定，涨跌幅非 0"""
    rows = await tencent_provider.fetch_hk_index_range(date(2026, 9, 3), date(2026, 9, 3))
    hsi = [r for r in rows if r["code"] == "HSI"]
    assert len(hsi) == 1
    assert hsi[0]["trade_date"] == date(2026, 9, 3)
    assert hsi[0]["change"] == 100.0
    assert hsi[0]["pct_chg"] == 0.5


@pytest.mark.asyncio
async def test_hk_range_multi_day(fake_kline):
    """多日区间各日涨跌幅依次差分，均为非 0"""
    rows = await tencent_provider.fetch_hk_index_range(date(2026, 9, 2), date(2026, 9, 3))
    hsi = sorted((r for r in rows if r["code"] == "HSI"), key=lambda r: r["trade_date"])
    assert [r["trade_date"] for r in hsi] == [date(2026, 9, 2), date(2026, 9, 3)]
    assert hsi[0]["change"] == 100.0  # 20000 - 19900
    assert hsi[1]["change"] == 100.0  # 20100 - 20000
    assert hsi[1]["pct_chg"] == 0.5


@pytest.mark.asyncio
async def test_hk_range_empty_series(monkeypatch):
    """数据源为空时静默返回空，不抛异常"""
    async def _empty(code, days):
        return None

    monkeypatch.setattr(tencent_provider, "fetch_hk_kline_rows", _empty)
    rows = await tencent_provider.fetch_hk_index_range(date(2026, 9, 3), date(2026, 9, 3))
    assert rows == []
