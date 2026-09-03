"""GET /api/overview —— 总览页全量数据（带 ETag 条件请求）"""

import hashlib
import json

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db import get_session
from app.schemas.overview import OverviewOut
from app.services import store
from app.services.aggregator import build_overview
from app.services.provider import ProviderError
from app.cache import overview_cache, DEFAULT_TTL, INTRADAY_TTL

router = APIRouter(tags=["总览"])


async def _resolve_ttl(session: AsyncSession, data_date: str) -> int:
    """按「数据是否真定格」选择缓存 TTL。

    is_settled 只看挂钟时间（15:05 后即视为已定格），但数据源（Tushare
    日线）要到 18:00 前后才更新当日数据，15:05~18:00 之间若按 24h 缓存，
    会把盘中脏数据锁死一整天。因此以「本地 L2 是否已有该日数据」为准：
    落库了才说明回填完成、数据不会再变。
    """
    try:
        d = date.fromisoformat(data_date)
    except ValueError:
        return INTRADAY_TTL
    if d < store.today_shanghai():
        return DEFAULT_TTL  # 历史交易日，已定格
    if store.is_settled(d) and await store.read_breadth(session, d) is not None:
        return DEFAULT_TTL  # 当日数据已落 L2，不会再变
    return INTRADAY_TTL  # 盘中 / 已收盘但 L2 尚未回填 → 60s 后重试


def _make_etag(data) -> str:
    """稳定 ETag：基于缓存数据的规范化 JSON 摘要（跨进程稳定）"""
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f'W/"{hashlib.md5(payload.encode("utf-8")).hexdigest()}"'


@router.get("/overview", response_model=OverviewOut)
async def get_overview(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """返回指数卡 + 分时对比 + 市场宽度 + 涨停 TOP + 行业 TOP5（收盘后直读本地库）"""
    cache_key = "overview"
    cached = overview_cache.get(cache_key)
    if cached is None:
        try:
            data = await build_overview(session)
        except ProviderError as e:
            raise HTTPException(503, f"暂无有效数据：{e}")
        cached = data.model_dump()
        overview_cache.set(
            cache_key, cached, await _resolve_ttl(session, cached["date"])
        )

    etag = _make_etag(cached)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=60"
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    return cached
