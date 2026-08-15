from __future__ import annotations

import logging
from typing import Optional

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import load_config
from backend.database import get_storage
from backend.models import RemyRun, RemyTask, _now

logger = logging.getLogger(__name__)

_scheduler: Optional["RemyScheduler"] = None


def get_scheduler() -> "RemyScheduler":
    global _scheduler
    if _scheduler is None:
        _scheduler = RemyScheduler()
    return _scheduler


def _tz_or_local() -> Optional[str]:
    """Return the configured timezone name, or None for server-local time."""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    tz_name = load_config().remy_tz
    if tz_name:
        try:
            ZoneInfo(tz_name)
            return tz_name
        except ZoneInfoNotFoundError:
            logger.warning("Unknown REMY_TZ %r, falling back to server-local time", tz_name)
    return None


async def _execute_task(task_id: str, trigger: str) -> RemyRun:
    """Execute a task, persisting a RemyRun with status/counts/errors."""
    storage = get_storage()
    run = RemyRun(task_id=task_id, trigger=trigger, status="running")
    await storage.save_remy_run(run)

    task = await storage.get_remy_task(task_id)
    if task is None:
        run.status = "failed"
        run.error = f"Task {task_id} not found"
        run.finished_at = _now()
        await storage.save_remy_run(run)
        return run

    if task.type != "scrape":
        run.status = "failed"
        run.error = f"Task type '{task.type}' is not implemented yet (Phase 4)"
        run.finished_at = _now()
        await storage.save_remy_run(run)
        logger.warning("Task %s skipped: %s", task_id, run.error)
        return run

    query = await storage.get_remy_query(task.query_id)
    if query is None:
        run.status = "failed"
        run.error = f"Query {task.query_id} not found"
        run.finished_at = _now()
        await storage.save_remy_run(run)
        return run
    if not query.enabled:
        run.status = "failed"
        run.error = f"Query {task.query_id} is disabled"
        run.finished_at = _now()
        await storage.save_remy_run(run)
        return run

    try:
        from backend.services.remy.scraper import run_query

        result = await run_query(query, storage)
    except Exception as e:
        logger.exception("Task %s execution failed", task_id)
        run.status = "failed"
        run.error = str(e)
        run.finished_at = _now()
        await storage.save_remy_run(run)
        return run

    run.listings_found = result.listings_found
    run.new_listings = result.new_listings
    run.status = "partial" if result.errors else "success"
    run.error = "; ".join(result.errors)
    run.log = "\n".join(
        f"{s.source}: found={s.found} new={s.new} updated={s.updated}"
        + (f" error={s.error}" if s.error else "")
        for s in result.by_source
    )
    run.finished_at = _now()
    await storage.save_remy_run(run)
    logger.info(
        "Task %s finished: %s (%d found, %d new)",
        task_id, run.status, run.listings_found, run.new_listings,
    )
    return run


def _cron_trigger(task: RemyTask, timezone: Optional[str]) -> CronTrigger:
    try:
        hour, minute = (int(p) for p in task.time.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 9, 0
    hour = max(0, min(hour, 23))
    minute = max(0, min(minute, 59))
    kwargs: dict = {"hour": hour, "minute": minute}
    if task.frequency == "weekly":
        kwargs["day_of_week"] = task.day_of_week
    return CronTrigger(**kwargs, timezone=timezone)


class RemyScheduler:
    """APScheduler-backed cron scheduler for Remy tasks (daily/weekly)."""

    def __init__(self) -> None:
        self._aps = AsyncIOScheduler()
        self._timezone = _tz_or_local()
        self._started = False

    @property
    def timezone(self) -> Optional[str]:
        return self._timezone

    async def start(self) -> None:
        """Load persisted tasks from storage and register cron jobs."""
        if self._started:
            return
        self._timezone = _tz_or_local()
        self._aps.start()
        self._started = True

        storage = get_storage()
        tasks = await storage.list_remy_tasks()
        for task in tasks:
            if task.enabled:
                try:
                    self._add_job(task)
                except Exception as e:
                    logger.warning("Could not schedule task %s: %s", task.id, e)
        if tasks:
            logger.info("RemyScheduler started with %d task(s), tz=%s", len(tasks), self._timezone)
        else:
            logger.info("RemyScheduler started, no tasks loaded")

    def stop(self) -> None:
        if self._started:
            self._aps.shutdown(wait=False)
            self._started = False
            logger.info("RemyScheduler stopped")

    async def reload(self) -> None:
        """Re-read tasks from storage and sync jobs (create/update/remove)."""
        self._timezone = _tz_or_local()
        storage = get_storage()
        tasks = await storage.list_remy_tasks()
        stored_ids = {t.id for t in tasks}
        for job in list(self._aps.get_jobs()):
            task_id = job.args[0] if job.args else None
            if task_id and task_id not in stored_ids:
                job.remove()
        for task in tasks:
            await self.sync_task(task)

    async def sync_task(self, task: RemyTask) -> None:
        """Schedule/update/remove a job to match the task's persisted state."""
        self._timezone = _tz_or_local()
        try:
            self._aps.remove_job(task.id)
        except JobLookupError:
            pass
        if task.enabled:
            self._add_job(task)

    def _add_job(self, task: RemyTask) -> None:
        async def _job() -> None:
            try:
                await _execute_task(task.id, "cron")
            except Exception as e:
                logger.exception("Scheduled task %s crashed: %s", task.id, e)

        self._aps.add_job(
            _job,
            trigger=_cron_trigger(task, self._timezone),
            id=task.id,
            name=f"remy:{task.type}:{task.query_id}",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
            replace_existing=True,
        )

    async def run_now(self, task_id: str) -> Optional[RemyRun]:
        """Execute a task immediately (manual trigger)."""
        storage = get_storage()
        task = await storage.get_remy_task(task_id)
        if task is None:
            return None
        return await _execute_task(task_id, "manual")
