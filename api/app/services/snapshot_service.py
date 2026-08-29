"""
快照入库（同日 upsert）+ 历史查询
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import SHANGHAI_TZ
from app.models.snapshot import DailySnapshot
from app.services.aggregator import build_overview
from app.schemas.overview import OverviewOut

logger = logging.getLogger(__name__)


async def save_daily_snapshot(session: AsyncSession) -> DailySnapshot:
    """收盘后抓全量快照并写入数据库（同一交易日重复执行时覆盖更新）"""
    overview = await build_overview()
    snap_date = datetime.now(SHANGHAI_TZ).date()
    data_json = overview.model_dump_json()

    stmt = select(DailySnapshot).where(DailySnapshot.snapshot_date == snap_date)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        existing.data_json = data_json
        existing.created_at = datetime.now(SHANGHAI_TZ)
        snapshot = existing
        logger.info("[Snapshot] 更新 %s 快照（同日重复执行）", snap_date)
    else:
        snapshot = DailySnapshot(
            snapshot_date=snap_date,
            data_json=data_json,
            created_at=datetime.now(SHANGHAI_TZ),
        )
        session.add(snapshot)

    await session.commit()
    await session.refresh(snapshot)
    return snapshot


async def get_snapshot_by_date(
    session: AsyncSession, dt
) -> OverviewOut | None:
    """按日期读取历史快照"""
    stmt = select(DailySnapshot).where(DailySnapshot.snapshot_date == dt)
    result = await session.execute(stmt)
    snap = result.scalar_one_or_none()
    if snap is None:
        return None
    return OverviewOut.model_validate_json(snap.data_json)
