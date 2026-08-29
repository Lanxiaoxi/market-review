"""历史复盘路由 —— 历史快照查询 / 手动快照 / 手动触发 L2 回填（写接口受 API Token 保护）"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import require_api_token
from app.models.db import get_session
from app.services.snapshot_service import get_snapshot_by_date, save_daily_snapshot
from app.schemas.overview import OverviewOut
from app.cache import clear_all

router = APIRouter(tags=["历史"])


@router.get("/history", response_model=OverviewOut)
async def get_history(
    dt: date = Query(alias="date"),
    session: AsyncSession = Depends(get_session),
):
    """按日期返回历史收盘快照"""
    snap = await get_snapshot_by_date(session, dt)
    if snap is None:
        raise HTTPException(404, f"未找到 {dt.isoformat()} 的快照")
    return snap


@router.post("/history/backfill", dependencies=[Depends(require_api_token)])
async def trigger_backfill(days: int = Query(250, ge=1, le=500)):
    """手动触发 L2 回填（首次上线补齐历史用）

    已回填的日期由 fetch_log 自动跳过，重复调用不会重复拉取。
    返回各域实际写入量，全为 0 表示无缺口。
    """
    from app.tasks import INTRADAY_CODES
    from app.services.backfill import run_backfill_days

    stats = await run_backfill_days(days, INTRADAY_CODES)
    if any(stats.values()):
        clear_all()
    return stats


@router.post("/history/snapshot", response_model=OverviewOut, dependencies=[Depends(require_api_token)])
async def create_snapshot(session: AsyncSession = Depends(get_session)):
    """手动触发收盘快照入库（同日重复执行会覆盖更新）"""
    from app.services.provider import ProviderError

    try:
        snap = await save_daily_snapshot(session)
    except ProviderError as e:
        raise HTTPException(503, f"暂无有效数据，快照未生成：{e}")
    return OverviewOut.model_validate_json(snap.data_json)
