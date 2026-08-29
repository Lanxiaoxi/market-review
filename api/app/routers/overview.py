"""GET /api/overview —— 总览页全量数据（带 ETag 条件请求）"""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db import get_session
from app.schemas.overview import OverviewOut
from app.services.aggregator import build_overview
from app.services.provider import ProviderError
from app.cache import overview_cache, DEFAULT_TTL

router = APIRouter(tags=["总览"])


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
        overview_cache.set(cache_key, cached, DEFAULT_TTL)

    etag = _make_etag(cached)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=60"
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    return cached
