"""GET /api/sectors —— 行业板块排名（当日/动量区间）+ 板块历史详情"""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db import get_session
from app.schemas.overview import SectorItemOut
from app.services.aggregator import build_sectors, build_sectors_range
from app.services import store
from app.services.provider import ProviderError
from app.cache import sectors_cache, DEFAULT_TTL

router = APIRouter(tags=["板块"])


def _make_etag(data) -> str:
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f'W/"{hashlib.md5(payload.encode("utf-8")).hexdigest()}"'


@router.get("/sectors", response_model=list[SectorItemOut])
async def get_sectors(
    request: Request,
    response: Response,
    sort: str = Query("pct", description="排序方式: pct(涨幅降序) / pct-asc(涨幅升序)"),
    range: int = Query(1, ge=1, le=60, description="统计区间交易日数: 1=当日 / 5=近5日 / 10=近10日 / 20=近20日"),
    session: AsyncSession = Depends(get_session),
):
    """行业板块涨跌排名（当日或 N 日动量区间，收盘后直读本地库零回源）"""
    cache_key = f"sectors:{sort}:r{range}"
    cached = sectors_cache.get(cache_key)
    if cached is None:
        try:
            data = (
                await build_sectors(session)
                if range <= 1
                else await build_sectors_range(session, range)
            )
        except ProviderError as e:
            raise HTTPException(503, f"暂无有效数据：{e}")
        if sort == "pct-asc":
            data.sort(key=lambda s: s.pct)
        else:
            data.sort(key=lambda s: s.pct, reverse=True)
        cached = [s.model_dump() for s in data]
        sectors_cache.set(cache_key, cached, DEFAULT_TTL)

    etag = _make_etag(cached)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=60"
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    return cached


@router.get("/sectors/{code}/history")
async def get_sector_history(
    code: str,
    days: int = Query(60, ge=7, le=250),
    session: AsyncSession = Depends(get_session),
):
    """单个板块近 days 个交易日收盘序列（板块详情图）"""
    rows = await store.read_sector_history(session, code, days)
    if not rows:
        raise HTTPException(404, f"板块 {code} 无历史数据")
    return {
        "code": code,
        "name": rows[-1].get("name", ""),
        "dates": [r["date"] for r in rows],
        "closes": [r["close"] for r in rows],
    }
