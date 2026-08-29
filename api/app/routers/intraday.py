"""GET /api/intraday?codes=sh000001,sh000300,sz399006 —— 指数当日分时（腾讯兜底，含 mock 回退）"""

import datetime

from fastapi import APIRouter, Query

from app.config import SHANGHAI_TZ
from app.schemas.intraday import IntradayOut, IntradaySeriesOut
from app.services.provider import fetch_domain, DOMAIN_INTRADAY
from app.cache import intraday_cache, DEFAULT_TTL, INTRADAY_TTL

router = APIRouter(tags=["分时"])


def _is_trading_hours() -> bool:
    """上海时区周一至周五 09:15–15:05 视为盘中（分时数据持续变化 → 短 TTL）"""
    now = datetime.datetime.now(SHANGHAI_TZ)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= minutes <= 15 * 60 + 5


@router.get("/intraday", response_model=IntradayOut)
async def get_intraday(
    codes: str = Query("sh000001", description="逗号分隔的腾讯行情代码，如 sh000001,sh000300,sz399006"),
):
    """返回多指数当日分时（价格 + 累计成交额），腾讯不可用时回退 mock"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        code_list = ["sh000001"]

    cache_key = f"intraday:{','.join(code_list)}"
    cached = intraday_cache.get(cache_key)
    if cached is not None:
        return IntradayOut(codes=cached)

    results = await fetch_domain(DOMAIN_INTRADAY, code_list)
    payload = {
        c: IntradaySeriesOut(**r)
        for c, r in results.items()
    }
    ttl = INTRADAY_TTL if _is_trading_hours() else DEFAULT_TTL
    intraday_cache.set(cache_key, payload, ttl)
    return IntradayOut(codes=payload)
