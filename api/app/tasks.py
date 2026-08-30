"""
APScheduler 收盘定时任务（周一至周五 18:00，Asia/Shanghai）

执行顺序：先回填 L2 持久层（补当日 + 补历史缺口），再落收盘快照。
先回填后快照，快照才能直接读本地库而不额外回源。
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.cache import clear_all
from app.models.db import async_session
from app.services.backfill import run_daily_job
from app.services.snapshot_service import save_daily_snapshot

logger = logging.getLogger(__name__)

# 显式指定上海时区：A 股 15:35 收盘快照不随服务器时区漂移
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 收盘后固化的分时代码（腾讯分钟线可用的 7 只 A 股指数；
# 中证2000 sh932000 腾讯无分钟线、港股不走本接口，故不在此列）
INTRADAY_CODES = [
    "sh000001",
    "sh000016",
    "sh000300",
    "sh000905",
    "sz399006",
    "sh000688",
    "sh000852",
]


async def _run_snapshot():
    """回填 L2 → 落收盘快照"""
    stats = await run_daily_job(intraday_codes=INTRADAY_CODES)
    logger.info("[Scheduler] L2 回填完成：%s", stats or "无新增")

    # L2 已更新，内存缓存里的旧数据必须失效，否则请求仍会拿到回填前的结果
    if any(stats.values()):
        clear_all()
        logger.info("[Scheduler] 已清空内存缓存")

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
        hour=18,
        minute=0,
        day_of_week="mon-fri",
        id="daily_snapshot",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] 收盘任务已启动（18:00 Asia/Shanghai，回填 + 快照）")


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
