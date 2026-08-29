"""GET /api/intraday?codes=sh000001,sh000300,sz399006 —— 指数当日分时（腾讯兜底）"""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import SHANGHAI_TZ
from app.models.db import get_session
from app.schemas.intraday import IntradayOut, IntradaySeriesOut
from app.services import store
from app.services.provider import fetch_domain, ProviderError, DOMAIN_INTRADAY
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
    session: AsyncSession = Depends(get_session),
):
    """返回多指数当日分时（价格 + 累计成交额），数据源不可用时 503

    收盘后由回填任务把当日分钟线固化入库，之后永久读本地，不再打腾讯接口。
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        code_list = ["sh000001"]

    cache_key = f"intraday:{','.join(code_list)}"
    cached = intraday_cache.get(cache_key)
    if cached is not None:
        return IntradayOut(codes=cached)

    # 已定格的分时数据：本地有完整覆盖就直接返回
    trade_date = await store.latest_trade_date(session)
    if store.is_settled(trade_date):
        local = await store.read_intraday(session, trade_date)
        if local is not None and set(code_list).issubset(local):
            payload = {
                c: IntradaySeriesOut(**local[c]) for c in code_list
            }
            intraday_cache.set(cache_key, payload, DEFAULT_TTL)
            return IntradayOut(codes=payload)

    try:
        results = await fetch_domain(DOMAIN_INTRADAY, code_list)
    except ProviderError as e:
        raise HTTPException(503, f"暂无有效数据：{e}")
    payload = {
        c: IntradaySeriesOut(**r)
        for c, r in results.items()
    }
    ttl = INTRADAY_TTL if _is_trading_hours() else DEFAULT_TTL
    intraday_cache.set(cache_key, payload, ttl)
    return IntradayOut(codes=payload)
