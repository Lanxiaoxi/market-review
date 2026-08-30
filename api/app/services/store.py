"""
L2 行情仓储层：交易日解析 + 按 trade_date 的读写闸门 + 本地聚合

设计契约（改动前请先读）：
1. 本模块所有 read_* 函数**只读本地库，绝不回源**；
   回源统一交给 backfill 服务，避免请求路径被 API 延迟拖住。
2. 所有 write_* 函数落库后必须调用 mark_fetched 登记 fetch_log，
   这是「同一份数据只拉一次」的唯一保证。
3. 交易日（trade_date）是主维度，不是 TTL：
   已定格的历史数据命中即返回，永不回源。

bulk 写入走 Core insert（executemany），单日全市场 5400 行 < 0.5s。
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Iterable, Sequence

from sqlalchemy import delete, func, select, text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import SHANGHAI_TZ
from app.models.market_data import (
    FetchLog,
    FuturesDaily,
    IndexDaily,
    IntradayBar,
    MarketDailyAgg,
    SectorDaily,
    SeriesCache,
    StockDaily,
    StockName,
    TradeCalendar,
    BondYield,
)
from app.services.buckets import DIST_LABELS, bucketize, normalize_sparkline

logger = logging.getLogger(__name__)

# 域常量：复用 provider 的命名，保证 fetch_log 与数据域一一对应
DOMAIN_BREADTH = "breadth"
DOMAIN_INDICES = "indices"
DOMAIN_SECTORS = "sectors"
DOMAIN_FUTURES = "futures"
DOMAIN_INTRADAY = "intraday"
DOMAIN_CALENDAR = "calendar"
DOMAIN_NAMES = "stock_names"

# 收盘后视为数据定格的时刻（上海时区，留 5 分钟给数据源落库）
_SETTLE_MINUTES = 15 * 60 + 5


# ────────────────────────── 交易日解析 ──────────────────────────


def today_shanghai() -> date:
    return datetime.now(SHANGHAI_TZ).date()


def is_settled(trade_date: date, now: datetime | None = None) -> bool:
    """该交易日的数据是否已定格（收盘后不再变化 → 可永久读本地）"""
    now = now or datetime.now(SHANGHAI_TZ)
    if trade_date < now.date():
        return True
    if trade_date > now.date():
        return False
    return now.hour * 60 + now.minute >= _SETTLE_MINUTES


def _fallback_weekday(ref: date) -> date:
    """日历为空时的兜底：向前找最近的工作日（不判断节假日）"""
    d = ref
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


async def load_calendar(session: AsyncSession) -> list[date]:
    """读取全部交易日历（升序）"""
    rows = await session.execute(
        select(TradeCalendar.trade_date)
        .where(TradeCalendar.is_open.is_(True))  # noqa: E712
        .order_by(TradeCalendar.trade_date)
    )
    return [r for r in rows.scalars().all()]


async def sync_calendar(session: AsyncSession, days: Sequence[date]) -> int:
    """写入交易日历（已存在的日期跳过）"""
    if not days:
        return 0
    existing = {
        r
        for r in (
            await session.execute(
                select(TradeCalendar.trade_date).where(TradeCalendar.trade_date.in_(set(days)))
            )
        )
        .scalars()
        .all()
    }
    new_rows = [
        {"trade_date": d, "is_open": True, "updated_at": datetime.now(SHANGHAI_TZ)}
        for d in days
        if d not in existing
    ]
    if not new_rows:
        return 0
    await session.execute(TradeCalendar.__table__.insert(), new_rows)
    await session.commit()
    return len(new_rows)


async def latest_trade_date(
    session: AsyncSession, ref: date | None = None
) -> date:
    """<= ref 的最近交易日；日历尚未同步时回退为最近工作日"""
    ref = ref or today_shanghai()
    row = (
        await session.execute(
            select(func.max(TradeCalendar.trade_date)).where(TradeCalendar.trade_date <= ref)
        )
    ).scalar_one_or_none()
    return row or _fallback_weekday(ref)


async def recent_trade_dates(
    session: AsyncSession, ref: date, n: int
) -> list[date]:
    """<= ref 的最近 n 个交易日（升序）；日历为空时返回 [ref]"""
    rows = (
        await session.execute(
            select(TradeCalendar.trade_date)
            .where(TradeCalendar.trade_date <= ref)
            .order_by(TradeCalendar.trade_date.desc())
            .limit(n)
        )
    ).scalars().all()
    dates = sorted(rows)
    return dates or [_fallback_weekday(ref)]


# ────────────────────────── fetch_log 去重闸门 ──────────────────────────


async def is_fetched(session: AsyncSession, domain: str, ref_key: str) -> bool:
    row = await session.get(FetchLog, (domain, ref_key))
    return row is not None


async def mark_fetched(
    session: AsyncSession,
    domain: str,
    ref_key: str,
    trade_date: date | None = None,
    source: str = "",
    rows_count: int = 0,
) -> None:
    """登记「已拉取」（幂等：重复调用只更新时间与来源）"""
    existing = await session.get(FetchLog, (domain, ref_key))
    if existing is not None:
        existing.fetched_at = datetime.now(SHANGHAI_TZ)
        existing.source = source or existing.source
        existing.rows_count = rows_count or existing.rows_count
    else:
        session.add(
            FetchLog(
                domain=domain,
                ref_key=ref_key,
                trade_date=trade_date,
                source=source,
                rows_count=rows_count,
                fetched_at=datetime.now(SHANGHAI_TZ),
            )
        )
    await session.commit()


async def missing_ref_keys(
    session: AsyncSession, domain: str, ref_keys: Sequence[str]
) -> list[str]:
    """从给定 ref_key 列表中筛出尚未拉取过的（差集）"""
    if not ref_keys:
        return []
    found = {
        r
        for r in (
            await session.execute(
                select(FetchLog.ref_key).where(
                    FetchLog.domain == domain, FetchLog.ref_key.in_(set(ref_keys))
                )
            )
        )
        .scalars()
        .all()
    }
    return [k for k in ref_keys if k not in found]


# ────────────────────────── 写入：个股日线 + 聚合 ──────────────────────────


async def save_stock_daily(
    session: AsyncSession,
    trade_date: date,
    rows: Sequence[dict],
    source: str = "",
) -> int:
    """写入全市场个股日线（同日先清后插，保证重复执行幂等）

    rows: [{"ts_code", "close", "pct_chg", "amount"}, ...]
    """
    if not rows:
        return 0
    await session.execute(delete(StockDaily).where(StockDaily.trade_date == trade_date))
    payload = [
        {
            "ts_code": str(r["ts_code"]),
            "trade_date": trade_date,
            "close": _f(r.get("close")),
            "pct_chg": _f(r.get("pct_chg")),
            "amount": _f(r.get("amount")),
        }
        for r in rows
    ]
    await session.execute(StockDaily.__table__.insert(), payload)
    await session.commit()
    return len(payload)


async def rebuild_market_agg(
    session: AsyncSession, trade_date: date, source: str = "", top_n: int = 5
) -> MarketDailyAgg | None:
    """由 stock_daily 重算该日全市场聚合（涨停 TOP5 需先有 stock_name 映射）"""
    rows = (
        await session.execute(
            select(StockDaily.ts_code, StockDaily.pct_chg, StockDaily.amount).where(
                StockDaily.trade_date == trade_date
            )
        )
    ).all()
    if not rows:
        return None

    counts = {label: 0 for label in DIST_LABELS}
    total_amount = 0.0
    top: list[tuple[float, str]] = []
    for ts_code, pct, amount in rows:
        if pct is None:
            continue
        pct_f = float(pct)
        label = bucketize(pct_f, ts_code)
        counts[label] += 1
        if amount is not None:
            total_amount += float(amount)
        if label == "涨停":
            top.append((pct_f, ts_code))

    up = counts["涨停"] + counts["涨2-10%"] + counts["涨0-2%"]
    down = counts["跌停"] + counts["跌2-10%"] + counts["跌0-2%"]
    flat = counts["平盘"]
    total = up + down + flat

    top.sort(reverse=True)
    top_codes = [c for _, c in top[:top_n]]
    name_map = await get_stock_names(session, top_codes)
    limit_up_top = [
        {"name": name_map.get(c) or c.split(".")[0], "pct": round(pct, 2)}
        for pct, c in top[:top_n]
    ]

    agg = MarketDailyAgg(
        trade_date=trade_date,
        up=up,
        down=down,
        flat=flat,
        up_pct=round(up / total * 100, 1) if total else 0,
        down_pct=round(down / total * 100, 1) if total else 0,
        flat_pct=round(flat / total * 100, 1) if total else 0,
        turnover_yi=round(total_amount / 1e5, 2),  # 千元 → 亿元
        limit_up=counts["涨停"],
        limit_down=counts["跌停"],
        limit_up_top=json.dumps(limit_up_top, ensure_ascii=False),
        dist_json=json.dumps(
            [{"label": k, "value": counts[k]} for k in DIST_LABELS], ensure_ascii=False
        ),
        source=source,
        updated_at=datetime.now(SHANGHAI_TZ),
    )
    merged = await session.merge(agg)
    await session.commit()
    return merged


async def sync_stock_names(session: AsyncSession, mapping: dict[str, str]) -> int:
    """批量 upsert 代码→名称映射"""
    if not mapping:
        return 0
    now = datetime.now(SHANGHAI_TZ)
    payload = [{"ts_code": k, "name": v, "updated_at": now} for k, v in mapping.items()]
    # 同 key 覆盖：先删后插最简单可靠（单日一次，量级 5000 行）
    await session.execute(delete(StockName).where(StockName.ts_code.in_(set(mapping))))
    await session.execute(StockName.__table__.insert(), payload)
    await session.commit()
    return len(payload)


async def get_stock_names(
    session: AsyncSession, codes: Iterable[str]
) -> dict[str, str]:
    codes = list(codes)
    if not codes:
        return {}
    rows = (
        await session.execute(
            select(StockName.ts_code, StockName.name).where(StockName.ts_code.in_(codes))
        )
    ).all()
    return dict(rows)


# ────────────────────────── 写入：指数 / 板块 / 期货 / 分时 ──────────────────────────


async def save_index_daily(
    session: AsyncSession,
    trade_date: date,
    rows: Sequence[dict],
    source: str = "",
) -> int:
    """rows: [{"ts_code", "code", "name", "close", "change", "pct_chg", "amount"}]"""
    if not rows:
        return 0
    await session.execute(delete(IndexDaily).where(IndexDaily.trade_date == trade_date))
    payload = [
        {
            "ts_code": str(r["ts_code"]),
            "trade_date": trade_date,
            "code": r.get("code") or str(r["ts_code"]).split(".")[0],
            "name": r.get("name", ""),
            "close": _f(r.get("close")) or 0,
            "change": _f(r.get("change")) or 0,
            "pct_chg": _f(r.get("pct_chg")) or 0,
            "amount": _f(r.get("amount")),
        }
        for r in rows
    ]
    await session.execute(IndexDaily.__table__.insert(), payload)
    await session.commit()
    return len(payload)


async def save_sector_daily(
    session: AsyncSession,
    trade_date: date,
    rows: Sequence[dict],
    source: str = "",
) -> int:
    """rows: [{"sector_code", "name", "close", "pct_chg", "leading"}]"""
    if not rows:
        return 0
    await session.execute(delete(SectorDaily).where(SectorDaily.trade_date == trade_date))
    payload = [
        {
            "sector_code": str(r["sector_code"]),
            "trade_date": trade_date,
            "name": r.get("name", ""),
            "close": _f(r.get("close")) or 0,
            "pct_chg": _f(r.get("pct_chg")) or 0,
            "leading": r.get("leading") or "—",
        }
        for r in rows
    ]
    await session.execute(SectorDaily.__table__.insert(), payload)
    await session.commit()
    return len(payload)


async def save_futures_daily(
    session: AsyncSession,
    contract: str,
    series: Sequence[dict],
    source: str = "",
) -> int:
    """series: [{"date": date|str, "close": float}]（按日覆盖写）"""
    if not series:
        return 0
    dates = [_as_date(s["date"]) for s in series]
    await session.execute(
        delete(FuturesDaily).where(
            FuturesDaily.contract == contract, FuturesDaily.trade_date.in_(dates)
        )
    )
    payload = [
        {"contract": contract, "trade_date": d, "close": _f(s["close"])}
        for d, s in zip(dates, series)
        if s.get("close") is not None
    ]
    if payload:
        await session.execute(FuturesDaily.__table__.insert(), payload)
        await session.commit()
    return len(payload)


async def save_intraday_bars(
    session: AsyncSession,
    trade_date: date,
    payload: dict[str, dict],
    source: str = "",
) -> int:
    """固化分时分钟线：payload = {code: {"times": [...], "prices": [...], "amounts": [...]}}"""
    rows = []
    for code, series in payload.items():
        for t, p, a in zip(series["times"], series["prices"], series["amounts"]):
            rows.append(
                {
                    "code": code,
                    "trade_date": trade_date,
                    "time": t,
                    "price": float(p),
                    "amount": float(a),
                }
            )
    if not rows:
        return 0
    await session.execute(delete(IntradayBar).where(IntradayBar.trade_date == trade_date))
    await session.execute(IntradayBar.__table__.insert(), rows)
    await session.commit()
    return len(rows)


# ────────────────────────── 读取（只读本地，绝不回源） ──────────────────────────


def _fmt_turnover(turnover_yi: float) -> str:
    """成交额格式化：亿元 → 万亿/亿"""
    if turnover_yi > 1e4:
        return f"{turnover_yi / 1e4:.2f}万亿"
    return f"{turnover_yi:.0f}亿"


async def read_breadth(session: AsyncSession, trade_date: date) -> dict | None:
    """返回与 provider.fetch_breadth 同构的 dict；无数据返回 None"""
    agg = await session.get(MarketDailyAgg, trade_date)
    if agg is None:
        return None
    return {
        "up": agg.up,
        "down": agg.down,
        "flat": agg.flat,
        "up_pct": agg.up_pct,
        "down_pct": agg.down_pct,
        "flat_pct": agg.flat_pct,
        "turnover": _fmt_turnover(agg.turnover_yi),
        "turnover_yi": agg.turnover_yi,
        "limit_up_count": agg.limit_up,
        "limit_down_count": agg.limit_down,
        "trade_date": trade_date.isoformat(),
        "dist": json.loads(agg.dist_json),
    }


async def read_limit_top(session: AsyncSession, trade_date: date) -> list[dict] | None:
    agg = await session.get(MarketDailyAgg, trade_date)
    if agg is None:
        return None
    return json.loads(agg.limit_up_top)


async def read_indices(
    session: AsyncSession, trade_date: date, lookback: int = 12
) -> list[dict] | None:
    """指数快照 + sparkline（用最近 lookback 个交易日收盘价）"""
    dates = await recent_trade_dates(session, trade_date, lookback)
    rows = (
        await session.execute(
            select(IndexDaily).where(IndexDaily.trade_date.in_(dates))
        )
    ).scalars().all()
    if not rows:
        return None

    by_code: dict[str, list[IndexDaily]] = {}
    for r in rows:
        by_code.setdefault(r.ts_code, []).append(r)

    result = []
    for ts_code, items in by_code.items():
        items.sort(key=lambda x: x.trade_date)
        if items[-1].trade_date != trade_date:
            continue  # 该指数当日无数据 → 不返回，避免混入过期快照
        latest = items[-1]
        result.append(
            {
                "code": latest.code or ts_code.split(".")[0],
                "name": latest.name,
                "value": round(latest.close, 2),
                "change": round(latest.change, 2),
                "change_pct": round(latest.pct_chg, 2),
                "sparkline": normalize_sparkline([i.close for i in items]),
                "closes": [round(i.close, 2) for i in items],  # 真实收盘价（升序，近 lookback 日）
            }
        )
    return result or None


def _sector_meta(items: list[SectorDaily]) -> dict:
    """板块异动标记：连涨/连跌天数（截至最新日，方向改变即停）+ 10 日新高/新低"""
    up_days = 0
    down_days = 0
    for it in reversed(items):
        p = it.pct_chg
        if p and p > 0:
            if down_days > 0:  # 方向已变为跌 → 涨势结束
                break
            up_days += 1
        elif p and p < 0:
            if up_days > 0:  # 方向已变为涨 → 跌势结束
                break
            down_days += 1
        else:
            break
    last10 = [i.close for i in items[-10:]]
    latest_close = items[-1].close
    return {
        "up_days": up_days,
        "down_days": down_days,
        "new_high_10d": bool(last10) and latest_close >= max(last10),
        "new_low_10d": bool(last10) and latest_close <= min(last10),
    }


async def read_sectors(session: AsyncSession, trade_date: date, lookback: int = 12) -> list[dict] | None:
    """行业板块排名 + sparkline（当日涨跌幅 + 异动标记）"""
    dates = await recent_trade_dates(session, trade_date, lookback)
    rows = (
        await session.execute(select(SectorDaily).where(SectorDaily.trade_date.in_(dates)))
    ).scalars().all()
    if not rows:
        return None

    by_code: dict[str, list[SectorDaily]] = {}
    for r in rows:
        by_code.setdefault(r.sector_code, []).append(r)

    result = []
    for sector_code, items in by_code.items():
        items.sort(key=lambda x: x.trade_date)
        if items[-1].trade_date != trade_date:
            continue
        latest = items[-1]
        result.append(
            {
                "code": sector_code,
                "name": latest.name,
                "pct": round(latest.pct_chg, 2),
                "leading": latest.leading or "—",
                "sparkline": normalize_sparkline([i.close for i in items]),
                **_sector_meta(items),
            }
        )
    return result or None


async def read_sectors_range(session: AsyncSession, trade_date: date, n: int) -> list[dict] | None:
    """行业板块 N 日区间涨幅排名（close[最新]/close[最新-N] - 1）

    历史不足 n+1 日的板块跳过；附带当日异动标记与 sparkline（与 read_sectors 同构）。
    """
    dates = await recent_trade_dates(session, trade_date, n + 1)
    rows = (
        await session.execute(select(SectorDaily).where(SectorDaily.trade_date.in_(dates)))
    ).scalars().all()
    if not rows:
        return None

    by_code: dict[str, list[SectorDaily]] = {}
    for r in rows:
        by_code.setdefault(r.sector_code, []).append(r)

    result = []
    for sector_code, items in by_code.items():
        items.sort(key=lambda x: x.trade_date)
        if items[-1].trade_date != trade_date or len(items) < n + 1:
            continue
        latest = items[-1]
        base = items[-(n + 1)].close
        result.append(
            {
                "code": sector_code,
                "name": latest.name,
                "pct": round((latest.close / base - 1) * 100, 2) if base else 0.0,
                "leading": latest.leading or "—",
                "sparkline": normalize_sparkline([i.close for i in items]),
                **_sector_meta(items),
            }
        )
    return result or None


async def read_sector_history(
    session: AsyncSession, sector_code: str, days: int
) -> list[dict] | None:
    """单个板块近 days 日收盘（升序，末条带名称）；无数据返回 None"""
    rows = (
        await session.execute(
            select(SectorDaily.trade_date, SectorDaily.close, SectorDaily.name)
            .where(SectorDaily.sector_code == sector_code)
            .order_by(SectorDaily.trade_date.desc())
            .limit(days)
        )
    ).all()
    if not rows:
        return None
    result = [{"date": d.isoformat(), "close": c} for d, c, _n in sorted(rows)]
    result[-1]["name"] = rows[0][2]  # 最新一条的名称
    return result


async def read_limit_counts(session: AsyncSession, days: int) -> list[dict] | None:
    """近 days 个交易日的涨停/跌停家数（直接读聚合表，零回源）"""
    rows = (
        await session.execute(
            select(
                MarketDailyAgg.trade_date,
                MarketDailyAgg.limit_up,
                MarketDailyAgg.limit_down,
            )
            .order_by(MarketDailyAgg.trade_date.desc())
            .limit(days)
        )
    ).all()
    if not rows:
        return None
    return [
        {"date": d.isoformat(), "limit_up": up, "limit_down": down}
        for d, up, down in sorted(rows)
    ]


async def read_breadth_series(session: AsyncSession, days: int) -> list[dict] | None:
    """近 days 个交易日的市场宽度序列（上涨/平盘/下跌家数，直接读聚合表，零回源）"""
    rows = (
        await session.execute(
            select(
                MarketDailyAgg.trade_date,
                MarketDailyAgg.up,
                MarketDailyAgg.flat,
                MarketDailyAgg.down,
            )
            .order_by(MarketDailyAgg.trade_date.desc())
            .limit(days)
        )
    ).all()
    if not rows:
        return None
    return [
        {"trade_date": d.isoformat(), "up": up, "flat": flat, "down": down}
        for d, up, flat, down in sorted(rows)
    ]


async def read_futures_series(
    session: AsyncSession, contract: str, days: int
) -> list[dict] | None:
    rows = (
        await session.execute(
            select(FuturesDaily.trade_date, FuturesDaily.close)
            .where(FuturesDaily.contract == contract)
            .order_by(FuturesDaily.trade_date.desc())
            .limit(days)
        )
    ).all()
    if not rows:
        return None
    return [{"date": d.isoformat(), "close": c} for d, c in sorted(rows)]


async def read_index_history(
    session: AsyncSession, ts_code: str, days: int
) -> list[dict] | None:
    rows = (
        await session.execute(
            select(IndexDaily.trade_date, IndexDaily.close)
            .where(IndexDaily.ts_code == ts_code)
            .order_by(IndexDaily.trade_date.desc())
            .limit(days)
        )
    ).all()
    if not rows:
        return None
    return [{"date": d.isoformat(), "close": c} for d, c in sorted(rows)]


async def read_52w_high_low(session: AsyncSession, days: int) -> list[dict] | None:
    """近 days 个交易日的 52 周新高/新低个股家数（滚动 250 日窗口，本地计算，零回源）

    窗口不足 250 日的早期日期按可用窗口计算（数值偏高，随数据积累变准）；
    全表一次窗口扫描约数秒，调用侧用 24h 缓存承接。
    """
    sql = text(
        """
        WITH ranked AS (
          SELECT ts_code, trade_date, close,
                 MAX(close) OVER (PARTITION BY ts_code ORDER BY trade_date ROWS BETWEEN 249 PRECEDING AND 1 PRECEDING) AS max_prior,
                 MIN(close) OVER (PARTITION BY ts_code ORDER BY trade_date ROWS BETWEEN 249 PRECEDING AND 1 PRECEDING) AS min_prior
          FROM stock_daily
        )
        SELECT trade_date,
               SUM(CASE WHEN max_prior IS NOT NULL AND close > max_prior THEN 1 ELSE 0 END) AS new_high,
               SUM(CASE WHEN min_prior IS NOT NULL AND close < min_prior THEN 1 ELSE 0 END) AS new_low
        FROM ranked
        WHERE trade_date IN (
          SELECT trade_date FROM (
            SELECT DISTINCT trade_date FROM stock_daily ORDER BY trade_date DESC LIMIT :days
          )
        )
        GROUP BY trade_date
        ORDER BY trade_date
        """
    )
    result = await session.execute(sql, {"days": days})
    rows = result.fetchall()
    if not rows:
        return None
    return [
        {
            "trade_date": str(r.trade_date)[:10],
            "new_high": int(r.new_high),
            "new_low": int(r.new_low),
        }
        for r in rows
    ]


async def read_stock_sparkline(
    session: AsyncSession, ts_code: str, days: int = 12
) -> list[float] | None:
    """个股 sparkline（自选页）；本地无数据返回 None 让调用方决定回源"""
    rows = (
        await session.execute(
            select(StockDaily.close)
            .where(StockDaily.ts_code == ts_code, StockDaily.close.is_not(None))
            .order_by(StockDaily.trade_date.desc())
            .limit(days)
        )
    ).scalars().all()
    if not rows:
        return None
    return normalize_sparkline([float(c) for c in reversed(rows)])


async def read_intraday(session: AsyncSession, trade_date: date) -> dict | None:
    """读取已固化的分时数据；无数据返回 None"""
    rows = (
        await session.execute(
            select(IntradayBar)
            .where(IntradayBar.trade_date == trade_date)
            .order_by(IntradayBar.code, IntradayBar.time)
        )
    ).scalars().all()
    if not rows:
        return None
    payload: dict[str, dict] = {}
    for r in rows:
        s = payload.setdefault(r.code, {"times": [], "prices": [], "amounts": []})
        s["times"].append(r.time)
        s["prices"].append(r.price)
        s["amounts"].append(r.amount)
    return payload


async def read_intraday_day(session: AsyncSession, code: str, trade_date: date) -> dict | None:
    """读取单日单指数分时（times HH:MM / prices / amounts）；无数据返回 None"""
    rows = (
        await session.execute(
            select(IntradayBar)
            .where(IntradayBar.trade_date == trade_date, IntradayBar.code == code)
            .order_by(IntradayBar.time)
        )
    ).scalars().all()
    if not rows:
        return None
    return {
        "times": [r.time for r in rows],
        "prices": [r.price for r in rows],
        "amounts": [r.amount for r in rows],
    }


async def save_bond_yield(
    session: AsyncSession,
    rows: Sequence[dict],
    source: str = "",
) -> int:
    """rows: [{"trade_date": date, "two_year", "five_year", "ten_year", "thirty_year"}]（按日覆盖写）"""
    if not rows:
        return 0
    dates = [_as_date(r["trade_date"]) for r in rows]
    await session.execute(delete(BondYield).where(BondYield.trade_date.in_(dates)))
    payload = [
        {
            "trade_date": d,
            "two_year": _f(r.get("two_year")),
            "five_year": _f(r.get("five_year")),
            "ten_year": _f(r.get("ten_year")),
            "thirty_year": _f(r.get("thirty_year")),
            "updated_at": datetime.now(SHANGHAI_TZ),
        }
        for r, d in zip(rows, dates)
    ]
    await session.execute(BondYield.__table__.insert(), payload)
    await session.commit()
    return len(payload)


async def read_bond_yield(session: AsyncSession, days: int) -> list[dict] | None:
    """近 days 个交易日的国债收益率（2/5/10/30 年期，升序）；无数据返回 None"""
    rows = (
        await session.execute(
            select(BondYield)
            .order_by(BondYield.trade_date.desc())
            .limit(days)
        )
    ).scalars().all()
    if not rows:
        return None
    result = [
        {
            "trade_date": r.trade_date.isoformat(),
            "two_year": r.two_year,
            "five_year": r.five_year,
            "ten_year": r.ten_year,
            "thirty_year": r.thirty_year,
        }
        for r in sorted(rows, key=lambda x: x.trade_date)
    ]
    return result or None


# ────────────────────────── series_cache 兜底 ──────────────────────────


async def cache_get(session: AsyncSession, key: str):
    row = await session.get(SeriesCache, key)
    if row is None:
        return None
    if row.expires_at is not None and datetime.now(SHANGHAI_TZ) > row.expires_at:
        return None
    try:
        return json.loads(row.payload)
    except json.JSONDecodeError:
        return None


async def cache_set(
    session: AsyncSession,
    key: str,
    payload,
    trade_date: date | None = None,
    ttl_seconds: int | None = None,
) -> None:
    now = datetime.now(SHANGHAI_TZ)
    expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds else None
    row = SeriesCache(
        cache_key=key,
        payload=json.dumps(payload, ensure_ascii=False),
        trade_date=trade_date,
        fetched_at=now,
        expires_at=expires_at,
    )
    await session.merge(row)
    await session.commit()


# ────────────────────────── 工具 ──────────────────────────


def _f(v):
    """转 float，None/空串/非法值统一为 None（SQLite 允许 NULL）"""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_date(v) -> date:
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    return date.fromisoformat(str(v)[:10])
