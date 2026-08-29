"""CRUD /api/watchlist —— 自选池 + 持仓盈亏（写接口受 API Token 保护）"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.auth import require_api_token
from app.cache import stock_sparkline_cache, DEFAULT_TTL
from app.models.db import get_session
from app.models.watchlist import WatchlistItem
from app.schemas.watchlist import (
    WatchlistItemOut,
    WatchlistSummaryOut,
    WatchlistResponse,
    WatchlistCreateIn,
    WatchlistUpdateIn,
)
from app.services.provider import fetch_domain, DOMAIN_STOCK_SPARKLINE

logger = logging.getLogger(__name__)

router = APIRouter(tags=["自选"])


async def _stock_sparkline(code: str) -> list[float]:
    """个股分时走势 sparkline（按代码缓存 24h；数据源不可用时返回空数组，不阻塞列表）"""
    cached = stock_sparkline_cache.get(code)
    if cached is not None:
        return cached
    try:
        data = await fetch_domain(DOMAIN_STOCK_SPARKLINE, code)
    except Exception as e:  # noqa: BLE001 —— sparkline 是增强字段，失败不影响主数据
        logger.warning("[Watchlist] 个股 %s sparkline 获取失败: %s", code, e)
        return []
    stock_sparkline_cache.set(code, data, DEFAULT_TTL)
    return data


def _item_out(r: WatchlistItem) -> WatchlistItemOut:
    return WatchlistItemOut(
        code=r.code,
        name=r.name,
        price=r.price,
        cost=r.cost,
        change_pct=r.change_pct,
        pnl=r.pnl,
        holding_value=r.holding_value,
        position_pct=r.position_pct,
    )


def _item_holding_pnl(r: WatchlistItem) -> float:
    """单只持仓盈亏（万）= 市值 × (现价 − 成本) / 现价；缺成本/现价时为 0"""
    if r.price <= 0 or r.cost <= 0:
        return 0.0
    return r.holding_value * (r.price - r.cost) / r.price


async def build_watchlist_response(session: AsyncSession) -> WatchlistResponse:
    stmt = select(WatchlistItem).order_by(WatchlistItem.sort_order)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    items = [_item_out(r) for r in rows]

    # 分时走势 sparkline：并发补充（尽力而为，失败为空数组）
    sparks = await asyncio.gather(*(_stock_sparkline(r.code) for r in rows))
    for item, sp in zip(items, sparks):
        item.sparkline = sp

    total_value = sum(r.holding_value for r in rows)
    today_pnl = sum(r.pnl for r in rows)
    holding_pnl = sum(_item_holding_pnl(r) for r in rows)
    position = round(min(100.0, sum(r.position_pct for r in rows)), 1)

    summary = WatchlistSummaryOut(
        total_value=round(total_value, 1),
        today_pnl=round(today_pnl, 1),
        holding_pnl=round(holding_pnl, 1),
        position=position,
    )

    return WatchlistResponse(items=items, summary=summary)


@router.get("/watchlist", response_model=WatchlistResponse)
async def list_watchlist(session: AsyncSession = Depends(get_session)):
    return await build_watchlist_response(session)


@router.post("/watchlist", response_model=WatchlistItemOut, status_code=201, dependencies=[Depends(require_api_token)])
async def create_watchlist(
    payload: WatchlistCreateIn,
    session: AsyncSession = Depends(get_session),
):
    # 防重复：code 唯一（迁移已建唯一索引，这里先做友好报错）
    dup = await session.execute(select(WatchlistItem).where(WatchlistItem.code == payload.code))
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(409, f"{payload.code} 已在自选中")

    max_order_result = await session.execute(
        select(WatchlistItem.sort_order).order_by(WatchlistItem.sort_order.desc()).limit(1)
    )
    max_order = max_order_result.scalar_one_or_none() or 0

    item = WatchlistItem(
        code=payload.code,
        name=payload.name,
        price=payload.price,
        cost=payload.cost,
        change_pct=payload.change_pct,
        pnl=payload.pnl,
        holding_value=payload.holding_value,
        position_pct=payload.position_pct,
        sort_order=max_order + 1,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return _item_out(item)


@router.put("/watchlist/{code}", response_model=WatchlistItemOut, dependencies=[Depends(require_api_token)])
async def update_watchlist(
    code: str,
    payload: WatchlistUpdateIn,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(WatchlistItem).where(WatchlistItem.code == code)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(404, "自选项目不存在")

    # CamelModel 默认按别名序列化，这里需要 snake_case 键去 setattr 模型字段
    update_data = payload.model_dump(exclude_unset=True, by_alias=False)
    if "name" in update_data and not str(update_data["name"]).strip():
        raise HTTPException(422, "名称不能为空")
    for key, val in update_data.items():
        setattr(item, key, val)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return _item_out(item)


@router.delete("/watchlist/{code}", status_code=204, dependencies=[Depends(require_api_token)])
async def delete_watchlist(
    code: str,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(WatchlistItem).where(WatchlistItem.code == code)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(404, "自选项目不存在")
    await session.delete(item)
    await session.commit()
