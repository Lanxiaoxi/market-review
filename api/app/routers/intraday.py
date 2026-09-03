"""GET /api/intraday?codes=sh000001,sh000300,sz399006&days=1 —— 指数分时（腾讯兜底 / 本地固化）"""

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


def _zero_day_segment() -> dict:
    """标准 A 股分钟网格（09:30–11:30 + 13:00–15:00，242 点）的 0 值占位段"""
    times: list[str] = []
    for h in range(9, 12):
        for m in range(0, 60):
            if h == 9 and m < 30:
                continue
            if h == 11 and m > 30:
                break
            times.append(f"{h:02d}:{m:02d}")
    for h in range(13, 16):
        for m in range(0, 60):
            if h == 15 and m > 0:
                break
            times.append(f"{h:02d}:{m:02d}")
    n = len(times)
    return {"times": times, "prices": [0.0] * n, "amounts": [0.0] * n}


@router.get("/intraday", response_model=IntradayOut)
async def get_intraday(
    codes: str = Query("sh000001", description="逗号分隔的腾讯行情代码，如 sh000001,sh000300,sz399006"),
    days: int = Query(1, ge=1, le=5, description="返回最近 N 个交易日分时（拼接，缺失日补 0）"),
    session: AsyncSession = Depends(get_session),
):
    """返回多指数当日/多日分时（价格 + 累计成交额），数据源不可用时 503

    days=1：收盘后读本地当日固化，盘中走腾讯实时（内存短 TTL）。
    days>1：最近 N 个交易日分时拼接（times 形如 "MM-DD HH:MM"），
    本地缺失的日期用 0 值占位——随每日 18:00 固化积累自动填满；最新日盘中未定格时实时兜底。
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        code_list = ["sh000001"]

    cache_key = f"intraday:{','.join(code_list)}:d{days}"
    cached = intraday_cache.get(cache_key)
    if cached is not None:
        return IntradayOut(codes=cached)

    if days <= 1:
        # 已定格的分时数据：本地有完整覆盖就直接返回
        trade_date = await store.latest_trade_date(session)
        if store.is_settled(trade_date):
            local = await store.read_intraday(session, trade_date)
            if local is not None and set(code_list).issubset(local):
                payload = {c: IntradaySeriesOut(**local[c]) for c in code_list}
                intraday_cache.set(cache_key, payload, DEFAULT_TTL)
                return IntradayOut(codes=payload)

        try:
            results = await fetch_domain(DOMAIN_INTRADAY, code_list)
        except ProviderError as e:
            raise HTTPException(503, f"暂无有效数据：{e}")
        payload = {c: IntradaySeriesOut(**r) for c, r in results.items()}
        ttl = INTRADAY_TTL if _is_trading_hours() else DEFAULT_TTL
        intraday_cache.set(cache_key, payload, ttl)
        return IntradayOut(codes=payload)

    # ─── 多日拼接：最近 N 个交易日分时 ───
    trade_date = await store.latest_trade_date(session)
    dates = await store.recent_trade_dates(session, trade_date, days)  # 升序
    if not dates:
        raise HTTPException(503, "暂无有效数据：无交易日")

    # 最新一日盘中未定格 → 实时兜底（一次拉全部代码）
    live: dict | None = None
    if not store.is_settled(dates[-1]):
        try:
            live = await fetch_domain(DOMAIN_INTRADAY, code_list)
        except ProviderError:
            live = None

    payload: dict[str, dict] = {}
    for code in code_list:
        times: list[str] = []
        prices: list[float] = []
        amounts: list[float] = []
        for d in dates:
            seg = await store.read_intraday_day(session, code, d)
            if seg is None and d == dates[-1] and live and code in live:
                seg = live[code]
            if seg is None:
                seg = _zero_day_segment()
            d_label = d.strftime("%m-%d")
            times.extend([f"{d_label} {t}" for t in seg["times"]])
            prices.extend(seg["prices"])
            amounts.extend(seg["amounts"])
        payload[code] = {"times": times, "prices": prices, "amounts": amounts}

    ttl = INTRADAY_TTL if _is_trading_hours() else DEFAULT_TTL
    intraday_cache.set(cache_key, payload, ttl)
    return IntradayOut(codes=payload)
