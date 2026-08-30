"""
回填测试用的确定性数据源：记录所有调用，便于断言「不重复获取」。

用 fake_fetch_domain 替换 backfill.fetch_domain 即可在完全离网的情况下
验证回填编排与 fetch_log 去重闸门。
"""

import datetime as dt

from app.config import SHANGHAI_TZ
from app.services import provider


def _past_trade_days(n: int = 5) -> list[dt.date]:
    """最近 n 个「已过去」的工作日（不含今天）

    用相对日期是为了让 is_settled() 恒为 True，
    否则盘中时段会走实时源，L2 断言就不成立了。
    """
    end = dt.datetime.now(SHANGHAI_TZ).date() - dt.timedelta(days=1)
    while end.weekday() >= 5:
        end -= dt.timedelta(days=1)
    days, cur = [], end
    while len(days) < n:
        if cur.weekday() < 5:
            days.append(cur)
        cur -= dt.timedelta(days=1)
    return sorted(days)


# 测试用的交易日（最近 5 个已过去的工作日）
TRADE_DAYS = _past_trade_days(5)

# 期现对比用到的现货指数（与 charts 路由的 FUTURES_CONTRACTS 对齐）
SPOT_INDEX_CODES = ["000300.SH", "000016.SH", "000852.SH"]

# 记录每次回源调用：(domain, args)
CALLS: list[tuple[str, tuple]] = []


def reset():
    CALLS.clear()


def _stock_rows(day: dt.date, n: int = 6) -> list[dict]:
    """每天 6 只票：2 涨停 / 1 跌停 / 3 下跌，保证聚合结果稳定可断言"""
    rows = []
    for i in range(n):
        if i < 2:
            pct = 10.0
        elif i == 2:
            pct = -10.0
        else:
            pct = -1.0 * (i - 2)
        rows.append(
            {
                "ts_code": f"{600000 + i}.SH",
                "close": 10.0 + i,
                "pct_chg": pct,
                "amount": 1_000_000.0,
            }
        )
    return rows


async def fake_fetch_domain(domain: str, *args, **kwargs):
    CALLS.append((domain, args))

    if domain == provider.DOMAIN_CALENDAR:
        return list(TRADE_DAYS)

    if domain == provider.DOMAIN_STOCK_DAILY_RAW:
        return _stock_rows(args[0])

    if domain == provider.DOMAIN_INDEX_RANGE:
        start, end = args
        out = []
        for i, d in enumerate(TRADE_DAYS):
            if not (start <= d <= end):
                continue
            for j, ts_code in enumerate(["000001.SH", *SPOT_INDEX_CODES]):
                out.append(
                    {
                        "ts_code": ts_code,
                        "code": ts_code.split(".")[0],
                        "name": f"指数{j}",
                        "trade_date": d,
                        "close": 3200.0 + i + j,
                        "change": 1.0,
                        "pct_chg": 0.03,
                        "amount": None,
                    }
                )
        return out

    if domain == provider.DOMAIN_SECTOR_RANGE:
        start, end = args
        return [
            {
                "sector_code": "881001",
                "name": "半导体",
                "trade_date": d,
                "close": 100.0 + i,
                "pct_chg": 1.5,
                "leading": "—",
            }
            for i, d in enumerate(TRADE_DAYS)
            if start <= d <= end
        ]

    if domain == provider.DOMAIN_STOCK_NAMES:
        return {f"{600000 + i}.SH": f"股票{i}" for i in range(6)}

    if domain == provider.DOMAIN_FUTURES_MAIN:
        contract, _days = args
        return [
            {"date": d.isoformat(), "close": 4000.0 + i}
            for i, d in enumerate(TRADE_DAYS)
        ]

    if domain == provider.DOMAIN_INTRADAY:
        codes = args[0]
        return {
            c: {
                "times": ["09:30", "09:31", "09:32"],
                "prices": [3200.0, 3201.0, 3202.0],
                "amounts": [1e8, 2e8, 3e8],
            }
            for c in codes
        }

    if domain == provider.DOMAIN_BOND_YIELD:
        start, end = args
        return [
            {
                "trade_date": d,
                "two_year": 1.2 + i * 0.01,
                "five_year": 1.4 + i * 0.01,
                "ten_year": 1.7 + i * 0.01,
                "thirty_year": 2.1 + i * 0.01,
            }
            for i, d in enumerate(TRADE_DAYS)
            if start <= d <= end
        ]

    raise AssertionError(f"fake_fetch_domain 未预期的域: {domain}")


def install(monkeypatch):
    """把 fake 装到 backfill 上，并去掉限流间隔让测试秒回"""
    import app.services.backfill as backfill

    reset()
    monkeypatch.setattr(backfill, "fetch_domain", fake_fetch_domain)
    monkeypatch.setattr(backfill, "DAY_GAP", 0)
    monkeypatch.setattr(backfill, "DOMAIN_GAP", 0)
    return CALLS
