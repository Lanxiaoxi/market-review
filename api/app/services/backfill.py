"""
回填服务：按 fetch_log 缺口把历史行情搬进 L2 持久层

核心原则
- **只补缺口**：每个域每次拉取前先查 fetch_log，已拉过的 (domain, ref_key) 直接跳过
- **区间优先**：指数/板块/期货按区间一次性拉（8~36 次请求覆盖一年），
  个股日线因单次请求即返回全市场某一天，按日串行拉（250 天 = 250 次请求）
- **失败不中断**：单日/单域失败只记日志，不影响其它域，下次运行自动重试
- **限流**：域间与日间插入间隔，避免触发 Tushare 频率限制 / THS 4001

首次上线跑 backfill(days=250)；日常由 15:35 定时任务调用 backfill(days=5)
（多留几天冗余，覆盖节假日与补漏）。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import SHANGHAI_TZ
from app.models.market_data import IndexDaily, SectorDaily
from app.services import store
from app.services.provider import (
    DOMAIN_BREADTH,
    DOMAIN_BOND_YIELD,
    DOMAIN_CALENDAR,
    DOMAIN_FUTURES_MAIN,
    DOMAIN_INDEX_RANGE,
    DOMAIN_INTRADAY,
    DOMAIN_SECTOR_RANGE,
    DOMAIN_STOCK_DAILY_RAW,
    DOMAIN_STOCK_NAMES,
    ProviderError,
    fetch_domain,
)

logger = logging.getLogger(__name__)

# 回填限流：日间与域间间隔（秒）
DAY_GAP = 0.25
DOMAIN_GAP = 0.5
# 单次回填最多补多少个交易日（防止误配触发全量拉取）
MAX_BACKFILL_DAYS = 500
# 期货主力合约：股指（IF/IH/IM）+ 国债（TS 2年/TF 5年/T 10年/TL 30年）
FUTURES_CONTRACTS = ("IF", "IH", "IM", "TS", "TF", "T", "TL")


def _ymd(d: date) -> str:
    return d.isoformat()


# ────────────────────────── 交易日历 ──────────────────────────


async def sync_calendar(session: AsyncSession, years_ahead: int = 1) -> int:
    """同步交易日历（按年登记，已同步的年份直接跳过）"""
    today = store.today_shanghai()
    years = range(today.year - 1, today.year + years_ahead + 1)
    todo = await store.missing_ref_keys(
        session, DOMAIN_CALENDAR, [f"{y}" for y in years]
    )
    if not todo:
        return 0

    start, end = date(int(todo[0]), 1, 1), date(int(todo[-1]), 12, 31)
    try:
        days = await fetch_domain(DOMAIN_CALENDAR, start, end)
    except ProviderError as e:
        logger.warning("[Backfill] 交易日历同步失败（下次重试）: %s", e)
        return 0

    added = await store.sync_calendar(session, days)
    for y in todo:
        await store.mark_fetched(session, DOMAIN_CALENDAR, y, source="calendar", rows_count=added)
    logger.info("[Backfill] 交易日历同步 %s 天（覆盖 %s）", added, ",".join(todo))
    return added


# ────────────────────────── 个股日线（按日）──────────────────────────


async def backfill_stock_daily(session: AsyncSession, dates: list[date]) -> int:
    """逐日回填全市场个股日线 + 重算当日聚合"""
    missing = await store.missing_ref_keys(
        session, DOMAIN_STOCK_DAILY_RAW, [_ymd(d) for d in dates]
    )
    if not missing:
        return 0
    todo = sorted(date.fromisoformat(k) for k in missing)

    done = 0
    for i, d in enumerate(todo):
        try:
            rows = await fetch_domain(DOMAIN_STOCK_DAILY_RAW, d)
        except ProviderError as e:
            logger.warning("[Backfill] 个股日线 %s 失败，跳过: %s", d, e)
            continue
        n = await store.save_stock_daily(session, d, rows, source=DOMAIN_STOCK_DAILY_RAW)
        await store.rebuild_market_agg(session, d, source=DOMAIN_STOCK_DAILY_RAW)
        await store.mark_fetched(
            session, DOMAIN_STOCK_DAILY_RAW, _ymd(d), trade_date=d,
            source=DOMAIN_STOCK_DAILY_RAW, rows_count=n,
        )
        done += 1
        if done % 20 == 0:
            logger.info("[Backfill] 个股日线进度 %s/%s", done, len(todo))
        if i < len(todo) - 1:
            await asyncio.sleep(DAY_GAP)
    if done:
        logger.info("[Backfill] 个股日线回填 %s 天", done)
    return done


# ────────────────────────── 指数 / 板块 / 期货（按区间）──────────────────────────


async def backfill_index_range(session: AsyncSession, start: date, end: date) -> int:
    """指数日线区间回填；按日登记 fetch_log，便于日常增量复用同一闸门"""
    dates = await _dates_in(session, start, end)
    missing = await store.missing_ref_keys(
        session, DOMAIN_INDEX_RANGE, [_ymd(d) for d in dates]
    )
    if not missing:
        return 0
    todo = sorted(date.fromisoformat(k) for k in missing)

    try:
        rows = await fetch_domain(DOMAIN_INDEX_RANGE, todo[0], todo[-1])
    except ProviderError as e:
        logger.warning("[Backfill] 指数日线区间失败，跳过: %s", e)
        return 0

    by_date: dict[date, list[dict]] = {}
    for r in rows:
        by_date.setdefault(r["trade_date"], []).append(r)

    written = 0
    for d, items in by_date.items():
        if d not in todo:
            continue
        n = await store.save_index_daily(session, d, items, source=DOMAIN_INDEX_RANGE)
        await store.mark_fetched(
            session, DOMAIN_INDEX_RANGE, _ymd(d), trade_date=d,
            source=DOMAIN_INDEX_RANGE, rows_count=n,
        )
        written += 1
    if written:
        logger.info("[Backfill] 指数日线回填 %s 天", written)
    return written


async def backfill_sector_range(session: AsyncSession, start: date, end: date) -> int:
    """行业日线区间回填（领涨股仅区间最后一日有值）"""
    dates = await _dates_in(session, start, end)
    missing = await store.missing_ref_keys(
        session, DOMAIN_SECTOR_RANGE, [_ymd(d) for d in dates]
    )
    if not missing:
        return 0
    todo = sorted(date.fromisoformat(k) for k in missing)

    try:
        rows = await fetch_domain(DOMAIN_SECTOR_RANGE, todo[0], todo[-1])
    except ProviderError as e:
        logger.warning("[Backfill] 行业日线区间失败，跳过: %s", e)
        return 0

    by_date: dict[date, list[dict]] = {}
    for r in rows:
        by_date.setdefault(r["trade_date"], []).append(r)

    written = 0
    for d, items in by_date.items():
        if d in todo:
            n = await store.save_sector_daily(session, d, items, source=DOMAIN_SECTOR_RANGE)
            await store.mark_fetched(
                session, DOMAIN_SECTOR_RANGE, _ymd(d), trade_date=d,
                source=DOMAIN_SECTOR_RANGE, rows_count=n,
            )
            written += 1
    if written:
        logger.info("[Backfill] 行业日线回填 %s 天", written)
    return written


async def backfill_futures(session: AsyncSession, days: int = 60) -> int:
    """股指/国债期货主力连续（按区间拉，整段覆盖写）

    ref_key 按合约 + 当天日期 → 每个合约每个自然日最多拉一次，新增合约可独立补齐。
    """
    today = store.today_shanghai()

    written = 0
    for contract in FUTURES_CONTRACTS:
        ref_key = f"{contract}:{_ymd(today)}:{days}d"
        if await store.is_fetched(session, DOMAIN_FUTURES_MAIN, ref_key):
            continue
        try:
            series = await fetch_domain(DOMAIN_FUTURES_MAIN, contract, days)
        except ProviderError as e:
            logger.warning("[Backfill] %s 主力连续失败，跳过: %s", contract, e)
            continue
        n = await store.save_futures_daily(session, contract, series, source=DOMAIN_FUTURES_MAIN)
        written += n
        await store.mark_fetched(
            session, DOMAIN_FUTURES_MAIN, ref_key,
            trade_date=today, source=DOMAIN_FUTURES_MAIN, rows_count=n,
        )
        await asyncio.sleep(DOMAIN_GAP)

    if written:
        logger.info("[Backfill] 期货主力连续回填 %s 行", written)
    return written


# ────────────────────────── 国债收益率（中债 CCDC）──────────────────────────


async def backfill_bond_yield(session: AsyncSession, start: date, end: date) -> int:
    """按缺口回填中债国债收益率曲线（按年分段请求，避免大范围高频）

    fetch_log 按日去重；每个缺失年份最多一次 POST，年份间插入 DOMAIN_GAP 间隔。
    """
    dates = await _dates_in(session, start, end)
    missing = await store.missing_ref_keys(
        session, DOMAIN_BOND_YIELD, [_ymd(d) for d in dates]
    )
    if not missing:
        return 0
    todo = sorted(date.fromisoformat(k) for k in missing)

    written = 0
    for y in sorted({d.year for d in todo}):
        y_start = max(start, date(y, 1, 1))
        y_end = min(end, date(y, 12, 31))
        try:
            rows = await fetch_domain(DOMAIN_BOND_YIELD, y_start, y_end)
        except ProviderError as e:
            logger.warning("[Backfill] 国债收益率 %s 年失败，跳过: %s", y, e)
            continue
        n = await store.save_bond_yield(session, rows, source=DOMAIN_BOND_YIELD)
        for r in rows:
            await store.mark_fetched(
                session, DOMAIN_BOND_YIELD, _ymd(r["trade_date"]),
                trade_date=r["trade_date"], source=DOMAIN_BOND_YIELD, rows_count=1,
            )
        written += n
        await asyncio.sleep(DOMAIN_GAP)
    if written:
        logger.info("[Backfill] 国债收益率回填 %s 天", written)
    return written


# ────────────────────────── 股票名称 / 分时固化 ──────────────────────────


async def sync_stock_names(session: AsyncSession) -> int:
    """同步代码→名称映射（每天一次，涨停 TOP5 展示用）"""
    today = store.today_shanghai()
    if await store.is_fetched(session, DOMAIN_STOCK_NAMES, _ymd(today)):
        return 0
    try:
        mapping = await fetch_domain(DOMAIN_STOCK_NAMES)
    except ProviderError as e:
        logger.warning("[Backfill] 股票名称同步失败，跳过: %s", e)
        return 0
    n = await store.sync_stock_names(session, mapping)
    await store.mark_fetched(
        session, DOMAIN_STOCK_NAMES, _ymd(today), trade_date=today,
        source=DOMAIN_STOCK_NAMES, rows_count=n,
    )
    return n


async def freeze_intraday(session: AsyncSession, trade_date: date, codes: list[str]) -> int:
    """收盘后固化当日分时（盘中数据由内存 TTL 承接，不落库）"""
    if await store.is_fetched(session, DOMAIN_INTRADAY, _ymd(trade_date)):
        return 0
    try:
        payload = await fetch_domain(DOMAIN_INTRADAY, codes)
    except ProviderError as e:
        logger.warning("[Backfill] 分时固化 %s 失败，跳过: %s", trade_date, e)
        return 0
    n = await store.save_intraday_bars(session, trade_date, payload, source=DOMAIN_INTRADAY)
    await store.mark_fetched(
        session, DOMAIN_INTRADAY, _ymd(trade_date), trade_date=trade_date,
        source=DOMAIN_INTRADAY, rows_count=n,
    )
    return n


# ────────────────────────── 编排入口 ──────────────────────────


async def _dates_in(session: AsyncSession, start: date, end: date) -> list[date]:
    """区间内的交易日（日历为空时退化为工作日序列）"""
    days = await store.recent_trade_dates(session, end, MAX_BACKFILL_DAYS)
    return [d for d in days if start <= d <= end]


async def backfill(
    session: AsyncSession,
    days: int = 250,
    intraday_codes: list[str] | None = None,
) -> dict[str, int]:
    """按缺口回填最近 days 个交易日的数据

    返回各域实际写入量，供日志/接口观察。
    """
    days = min(days, MAX_BACKFILL_DAYS)
    stats: dict[str, int] = {}

    stats["calendar"] = await sync_calendar(session)
    await asyncio.sleep(DOMAIN_GAP)

    end = await store.latest_trade_date(session)
    window = await store.recent_trade_dates(session, end, days)
    start = window[0] if window else end

    stats["stock_names"] = await sync_stock_names(session)
    await asyncio.sleep(DOMAIN_GAP)

    stats["stock_daily"] = await backfill_stock_daily(session, window)
    await asyncio.sleep(DOMAIN_GAP)

    stats["index_daily"] = await backfill_index_range(session, start, end)
    await asyncio.sleep(DOMAIN_GAP)

    stats["sector_daily"] = await backfill_sector_range(session, start, end)
    await asyncio.sleep(DOMAIN_GAP)

    stats["futures"] = await backfill_futures(session, days=max(days, 60))
    await asyncio.sleep(DOMAIN_GAP)

    # 国债收益率：按缺口补（首次全量按年分段，日常仅最新几日）
    stats["bond_yield"] = await backfill_bond_yield(session, start, end)

    # 分时固化：仅在当日已定格（收盘后）时执行
    if intraday_codes and store.is_settled(end):
        stats["intraday"] = await freeze_intraday(session, end, intraday_codes)

    logger.info("[Backfill] 完成：%s", stats)
    return stats


async def run_backfill_days(
    days: int, intraday_codes: list[str] | None = None
) -> dict[str, int]:
    """按指定天数回填（首次上线 / 手动触发用），自带 session"""
    from app.models.db import async_session

    async with async_session() as session:
        try:
            return await backfill(session, days=days, intraday_codes=intraday_codes)
        except Exception as e:  # noqa: BLE001 —— 回填失败不应拖垮调用方
            logger.exception("[Backfill] 回填 %s 天失败: %s", days, e)
            return {}


async def run_daily_job(intraday_codes: list[str] | None = None) -> dict[str, int]:
    """定时任务入口：自带 session，回填近 5 个交易日（覆盖节假日与补漏）"""
    from app.models.db import async_session

    async with async_session() as session:
        try:
            return await backfill(session, days=5, intraday_codes=intraday_codes)
        except Exception as e:  # noqa: BLE001 —— 定时任务不能因单点异常而停摆
            logger.exception("[Backfill] 定时任务执行失败: %s", e)
            return {}
