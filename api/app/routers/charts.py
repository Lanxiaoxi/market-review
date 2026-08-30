"""图表数据路由 —— 期现对比 / 涨跌停家数 / 市场宽度（读本地 L2，零回源）"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.cache import charts_cache, DEFAULT_TTL
from app.models.db import get_session
from app.services import store
from app.schemas.charts import (
    IfBasisOut,
    LimitCountsOut,
    BreadthSeriesOut,
)
from app.services.provider import (
    fetch_domain,
    DOMAIN_INDEX_HISTORY,
    DOMAIN_FUTURES_MAIN,
    DOMAIN_LIMIT_COUNTS,
)

router = APIRouter(tags=["图表"])

# 中金所股指期货合约 → 现货指数
FUTURES_CONTRACTS: dict[str, dict[str, str]] = {
    "IF": {"spot": "000300.SH", "name": "沪深300"},
    "IH": {"spot": "000016.SH", "name": "上证50"},
    "IM": {"spot": "000852.SH", "name": "中证1000"},
}


def _align_series(
    spot_series: list[dict], fut_series: list[dict]
) -> tuple[list[str], list[float], list[float]]:
    """按日期对齐现货与期货序列（现货日期为主，期货缺失日跳过）"""
    fut_by_date = {f["date"]: f["close"] for f in fut_series}
    dates, spot, futures = [], [], []
    for s in spot_series:
        f = fut_by_date.get(s["date"])
        if f is not None:
            dates.append(s["date"])
            spot.append(round(float(s["close"]), 2))
            futures.append(round(float(f), 2))
    return dates, spot, futures


@router.get("/charts/futures-basis", response_model=IfBasisOut)
async def get_futures_basis(
    contract: str = Query("IF", description="中金所合约: IF(沪深300) / IH(上证50) / IM(中证1000)"),
    days: int = Query(60, ge=7, le=250),
    session: AsyncSession = Depends(get_session),
):
    """股指期货期现对比（日线）：现货指数 vs 中金所主力合约，基差率附随

    优先读 L2（index_daily + futures_daily），本地缺失才回源。
    """
    key = contract.upper()
    if key not in FUTURES_CONTRACTS:
        raise HTTPException(422, f"不支持的合约: {contract}（可选 IF/IH/IM）")

    cache_key = f"futures-basis:{key}:{days}"
    cached = charts_cache.get(cache_key)
    if cached is not None:
        return IfBasisOut(**cached)

    spot_code = FUTURES_CONTRACTS[key]["spot"]
    spot_series = await store.read_index_history(session, spot_code, days)
    if spot_series is None:
        spot_series = await fetch_domain(DOMAIN_INDEX_HISTORY, spot_code, days)

    fut_series = await store.read_futures_series(session, key, days)
    if fut_series is None:
        fut_series = await fetch_domain(DOMAIN_FUTURES_MAIN, key, days)

    dates, spot, futures = _align_series(spot_series, fut_series)
    if not dates:
        raise HTTPException(502, "期现数据为空，请稍后重试")

    premium = [round((f - s) / s * 100, 3) for s, f in zip(spot, futures)]
    basis = [round(s - f, 2) for s, f in zip(spot, futures)]  # 基差（点）= 现货 - 期货
    payload = {
        "contract": key,
        "name": FUTURES_CONTRACTS[key]["name"],
        "dates": dates,
        "spot": spot,
        "futures": futures,
        "basis": basis,
        "premium": premium,
    }
    charts_cache.set(cache_key, payload, DEFAULT_TTL)
    return IfBasisOut(**payload)


@router.get("/charts/if-basis", response_model=IfBasisOut, include_in_schema=False)
async def get_if_basis_alias(
    days: int = Query(60, ge=7, le=250),
    session: AsyncSession = Depends(get_session),
):
    """旧路径兼容：/charts/if-basis == /charts/futures-basis?contract=IF"""
    return await get_futures_basis(contract="IF", days=days, session=session)


@router.get("/charts/limit-counts", response_model=LimitCountsOut)
async def get_limit_counts(
    days: int = Query(60, ge=7, le=250),
    session: AsyncSession = Depends(get_session),
):
    """日线涨停/跌停家数序列（近 days 个交易日）

    本地 market_daily_agg 直接聚合，命中即返回 —— 这是全站回源次数最多的接口，
    改造前每次冷启动要按天打 2×days 次涨停池/跌停池接口。
    """
    cache_key = f"limit-counts:{days}"
    cached = charts_cache.get(cache_key)
    if cached is not None:
        return LimitCountsOut(**cached)

    rows = await store.read_limit_counts(session, days)
    if rows is None:
        rows = await fetch_domain(DOMAIN_LIMIT_COUNTS, days)
    if not rows:
        raise HTTPException(502, "涨跌停家数数据为空，请稍后重试")

    payload = {
        "dates": [r["date"] for r in rows],
        "limit_up": [r["limit_up"] for r in rows],
        "limit_down": [r["limit_down"] for r in rows],
    }
    charts_cache.set(cache_key, payload, DEFAULT_TTL)
    return LimitCountsOut(**payload)


@router.get("/charts/breadth-series", response_model=BreadthSeriesOut)
async def get_breadth_series(
    days: int = Query(60, ge=7, le=250),
    session: AsyncSession = Depends(get_session),
):
    """日线市场宽度序列（上涨/平盘/下跌家数，近 days 个交易日）

    本地 market_daily_agg 直接聚合，命中即返回（零回源）。
    """
    cache_key = f"breadth-series:{days}"
    cached = charts_cache.get(cache_key)
    if cached is not None:
        return BreadthSeriesOut(**cached)

    rows = await store.read_breadth_series(session, days)
    if not rows:
        raise HTTPException(502, "市场宽度数据为空，请稍后重试")

    payload = {
        "dates": [r["trade_date"] for r in rows],
        "up": [r["up"] for r in rows],
        "flat": [r["flat"] for r in rows],
        "down": [r["down"] for r in rows],
    }
    charts_cache.set(cache_key, payload, DEFAULT_TTL)
    return BreadthSeriesOut(**payload)
