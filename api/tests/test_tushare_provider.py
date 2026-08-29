"""
tushare_provider 单元测试（不触网，用桩对象验证关键逻辑）
"""

import pandas as pd
import pytest

from app.services import tushare_provider as tp


class FakePro:
    """模拟 Tushare pro_api：trade_cal 返回降序（实测行为）"""

    def __init__(self, cal_df: pd.DataFrame):
        self._cal = cal_df

    def trade_cal(self, **kwargs):
        return self._cal


def _cal_df(cal_dates, is_open):
    return pd.DataFrame({"exchange": "SSE", "cal_date": cal_dates, "is_open": is_open})


def test_latest_trade_date_descending_order():
    """trade_cal 降序返回时，必须取窗口内最新交易日（回归：曾取到最早一天）"""
    pro = FakePro(_cal_df(
        ["20260828", "20260827", "20260826", "20260825", "20260824", "20260821", "20260820",
         "20260819", "20260818", "20260817", "20260814"],
        [1] * 11,
    ))
    assert tp._latest_trade_date(pro) == "20260828"


def test_latest_trade_date_ascending_order():
    """trade_cal 升序返回时行为一致"""
    pro = FakePro(_cal_df(
        ["20260814", "20260817", "20260818", "20260819", "20260820", "20260821", "20260824",
         "20260825", "20260826", "20260827", "20260828"],
        [1] * 11,
    ))
    assert tp._latest_trade_date(pro) == "20260828"


def test_latest_trade_date_weekend_fallback():
    """trade_cal 返回空时回退到最近工作日（周六 08-29 → 周五 08-28）"""
    pro = FakePro(_cal_df([], []))  # 空日历 → 走 fallback

    import datetime as _dt

    class _FixedToday(_dt.date):
        @classmethod
        def today(cls):
            return _dt.date(2026, 8, 29)  # 周六

    orig_today = tp.datetime.date
    tp.datetime.date = _FixedToday
    try:
        assert tp._latest_trade_date(pro) == "20260828"
    finally:
        tp.datetime.date = orig_today
