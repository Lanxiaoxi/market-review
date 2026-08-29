"""CRUD /api/charts —— 图表库列表 + 钉选配置 + 期现对比数据（写接口受 API Token 保护）"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.auth import require_api_token
from app.cache import charts_cache, DEFAULT_TTL
from app.models.db import get_session
from app.models.chart_config import ChartConfig
from app.schemas.charts import (
    ChartLibItemOut,
    ChartCreateIn,
    ChartUpdateIn,
    IfBasisOut,
    LimitCountsOut,
)
from app.services.provider import (
    fetch_domain,
    DOMAIN_INDEX_HISTORY,
    DOMAIN_FUTURES_MAIN,
    DOMAIN_LIMIT_COUNTS,
)

router = APIRouter(tags=["图表库"])

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
    days: int = Query(60, ge=10, le=250),
):
    """股指期货期现对比（日线）：现货指数 vs 中金所主力合约，基差率附随"""
    key = contract.upper()
    if key not in FUTURES_CONTRACTS:
        raise HTTPException(422, f"不支持的合约: {contract}（可选 IF/IH/IM）")

    cache_key = f"futures-basis:{key}:{days}"
    cached = charts_cache.get(cache_key)
    if cached is not None:
        return IfBasisOut(**cached)

    spot_series = await fetch_domain(DOMAIN_INDEX_HISTORY, FUTURES_CONTRACTS[key]["spot"], days)
    fut_series = await fetch_domain(DOMAIN_FUTURES_MAIN, key, days)
    dates, spot, futures = _align_series(spot_series, fut_series)
    if not dates:
        raise HTTPException(502, "期现数据为空，请稍后重试")

    premium = [round((f - s) / s * 100, 3) for s, f in zip(spot, futures)]
    payload = {
        "contract": key,
        "name": FUTURES_CONTRACTS[key]["name"],
        "dates": dates,
        "spot": spot,
        "futures": futures,
        "premium": premium,
    }
    charts_cache.set(cache_key, payload, DEFAULT_TTL)
    return IfBasisOut(**payload)


@router.get("/charts/if-basis", response_model=IfBasisOut, include_in_schema=False)
async def get_if_basis_alias(days: int = Query(60, ge=10, le=250)):
    """旧路径兼容：/charts/if-basis == /charts/futures-basis?contract=IF"""
    return await get_futures_basis(contract="IF", days=days)


@router.get("/charts/limit-counts", response_model=LimitCountsOut)
async def get_limit_counts(days: int = Query(60, ge=10, le=250)):
    """日线涨停/跌停家数序列（近 days 个交易日）"""
    cache_key = f"limit-counts:{days}"
    cached = charts_cache.get(cache_key)
    if cached is not None:
        return LimitCountsOut(**cached)

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


@router.get("/charts", response_model=list[ChartLibItemOut])
async def list_charts(session: AsyncSession = Depends(get_session)):
    stmt = select(ChartConfig)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        ChartLibItemOut(
            id=row.chart_id,
            name=row.name,
            type=row.chart_type,
            pinned=row.pinned,
        )
        for row in rows
    ]


@router.post("/charts", response_model=ChartLibItemOut, status_code=201, dependencies=[Depends(require_api_token)])
async def create_chart(
    payload: ChartCreateIn,
    session: AsyncSession = Depends(get_session),
):
    chart_id = payload.id or str(uuid.uuid4())[:12]
    # 防重复：chart_id 唯一
    dup = await session.execute(select(ChartConfig).where(ChartConfig.chart_id == chart_id))
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(409, f"图表 {chart_id} 已存在")

    config = ChartConfig(
        chart_id=chart_id,
        name=payload.name,
        chart_type=payload.type,
        pinned=payload.pinned,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return ChartLibItemOut(
        id=config.chart_id,
        name=config.name,
        type=config.chart_type,
        pinned=config.pinned,
    )


@router.put("/charts/{chart_id}", response_model=ChartLibItemOut, dependencies=[Depends(require_api_token)])
async def update_chart(
    chart_id: str,
    payload: ChartUpdateIn,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ChartConfig).where(ChartConfig.chart_id == chart_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(404, "图表不存在")

    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(config, key, val)

    session.add(config)
    await session.commit()
    await session.refresh(config)
    return ChartLibItemOut(
        id=config.chart_id,
        name=config.name,
        type=config.chart_type,
        pinned=config.pinned,
    )


@router.delete("/charts/{chart_id}", status_code=204, dependencies=[Depends(require_api_token)])
async def delete_chart(
    chart_id: str,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ChartConfig).where(ChartConfig.chart_id == chart_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(404, "图表不存在")
    await session.delete(config)
    await session.commit()
