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
