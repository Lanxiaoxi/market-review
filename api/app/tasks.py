"""
APScheduler 收盘快照定时任务（周一至周五 15:35，Asia/Shanghai）
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models.db import async_session
from app.services.snapshot_service import save_daily_snapshot

logger = logging.getLogger(__name__)

# 显式指定上海时区：A 股 15:35 收盘快照不随服务器时区漂移
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def _run_snapshot():
    """执行收盘快照"""
    async with async_session() as session:
        try:
            snap = await save_daily_snapshot(session)
            logger.info("[Snapshot] 已保存 %s 快照", snap.snapshot_date)
        except Exception as e:
            logger.exception("[Snapshot] 执行失败: %s", e)


def start_scheduler():
    """注册定时任务 → 每个工作日 15:35（上海时区）"""
    if scheduler.running:
        return
    scheduler.add_job(
        _run_snapshot,
        trigger="cron",
        hour=15,
        minute=35,
        day_of_week="mon-fri",
        id="daily_snapshot",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] 收盘快照任务已启动（15:35 Asia/Shanghai）")


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
