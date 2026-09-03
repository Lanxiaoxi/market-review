"""
收盘定时任务的缓存失效：无条件清空。

run_daily_job 内部异常时被 catch 成 {} 返回，若按「有没有新增数据」判断，
脏缓存反而会稳稳留到第二天。缓存该不该失效与回填有没有新增无关——
调度触发时点之后，缓存里的任何内容都不可信。
"""

import pytest

from app.cache import clear_all
from app.tasks import _run_snapshot


@pytest.mark.asyncio
async def test_cache_cleared_even_when_nothing_backfilled(monkeypatch):
    """回填无新增（或内部异常返回 {}）时，缓存同样要清空"""
    calls = {"clear": 0, "snapshot": 0}

    async def _no_new_rows(*args, **kwargs):
        return {}

    async def _save(session):
        calls["snapshot"] += 1

    monkeypatch.setattr("app.tasks.run_daily_job", _no_new_rows)
    monkeypatch.setattr("app.tasks.clear_all", lambda: calls.__setitem__("clear", calls["clear"] + 1))
    monkeypatch.setattr("app.tasks.save_daily_snapshot", _save)

    await _run_snapshot()

    assert calls["clear"] == 1, "回填无新增也必须清空缓存"
    assert calls["snapshot"] == 1, "快照仍应正常落库"


@pytest.mark.asyncio
async def test_cache_cleared_when_backfill_succeeded(monkeypatch):
    """回填有新增时照常清空"""
    calls = {"clear": 0}

    async def _with_rows(*args, **kwargs):
        return {"stock_daily": 5200, "index_daily": 8}

    async def _save(session):
        return None

    monkeypatch.setattr("app.tasks.run_daily_job", _with_rows)
    monkeypatch.setattr("app.tasks.clear_all", lambda: calls.__setitem__("clear", calls["clear"] + 1))
    monkeypatch.setattr("app.tasks.save_daily_snapshot", _save)

    await _run_snapshot()

    assert calls["clear"] == 1


@pytest.mark.asyncio
async def test_snapshot_job_runs_at_18_not_1535():
    """调度必须落在 18:00

    15:35 回填会拉到数据源尚未更新的当日数据，而 fetch_log 一旦把该日
    标记成已抓取，之后即使数据更新也不会再补。
    """
    from app.tasks import scheduler, shutdown_scheduler, start_scheduler

    try:
        start_scheduler()
        job = scheduler.get_job("daily_snapshot")
        assert job is not None, "收盘任务未注册"
        desc = str(job.trigger)
        assert "hour='18'" in desc, f"调度小时不是 18: {desc}"
        assert "minute='0'" in desc, f"调度分钟不是 0: {desc}"
        assert "mon-fri" in desc, f"未按工作日调度: {desc}"
    finally:
        shutdown_scheduler()


@pytest.mark.asyncio
async def test_snapshot_failure_does_not_raise(monkeypatch):
    """快照落库失败不应让整个定时任务抛出（下次调度仍可执行）"""
    async def _no_new_rows(*args, **kwargs):
        return {}

    async def _boom(session):
        raise RuntimeError("db down")

    monkeypatch.setattr("app.tasks.run_daily_job", _no_new_rows)
    monkeypatch.setattr("app.tasks.clear_all", clear_all)
    monkeypatch.setattr("app.tasks.save_daily_snapshot", _boom)

    await _run_snapshot()  # 不应抛出
