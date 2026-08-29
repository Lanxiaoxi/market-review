"""GET /api/sectors?sort=pct —— 申万一级行业排名（带 ETag 条件请求）"""

import hashlib
import json

from fastapi import APIRouter, Query, Request, Response

from app.schemas.overview import SectorItemOut
from app.services.aggregator import build_sectors
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
):
    """返回申万一级行业涨跌排名"""
    cache_key = f"sectors:{sort}"
    cached = sectors_cache.get(cache_key)
    if cached is None:
        data = await build_sectors()
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
