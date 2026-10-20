import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.metrics import QUEUE_DEPTH, SCHEDULER_ENQUEUED, SCHEDULER_LAST_SUCCESS
from app.models.base import utcnow
from app.models.execution import Run
from app.models.project import Monitor
from app.services.locks import acquire_scheduler_lock, release_scheduler_lock
from app.workers.dispatch import dispatch_run


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _record_queue_depth() -> None:
    try:
        from app.services.locks import _client

        QUEUE_DEPTH.set(_client().llen("release_guardian"))
    except Exception:  # noqa: BLE001 - queue metrics are best-effort
        return


def enqueue_due_monitors(db: Session | None = None) -> dict:
    acquired, lock_token = acquire_scheduler_lock()
    if not acquired:
        return {"queued": 0, "run_ids": [], "skipped": "lock_held"}

    owned = db is None
    session = db or SessionLocal()
    created: list[str] = []
    try:
        now = utcnow()
        monitors = session.query(Monitor).filter(Monitor.enabled.is_(True)).all()
        for monitor in monitors:
            last = _as_utc(monitor.last_checked_at)
            if last is not None and (now - last).total_seconds() < monitor.interval_seconds:
                continue

            active = (
                session.query(Run)
                .filter(
                    Run.monitor_id == monitor.id,
                    Run.status.in_(["pending", "running"]),
                )
                .first()
            )
            if active is not None:
                continue

            run = Run(
                monitor_id=monitor.id,
                environment_id=monitor.environment_id,
                status="pending",
                trigger="scheduled",
            )
            session.add(run)
            session.flush()
            created.append(run.id)
        session.commit()
    finally:
        if owned:
            session.close()
        release_scheduler_lock(lock_token)

    for run_id in created:
        dispatch_run(run_id)

    if created:
        SCHEDULER_ENQUEUED.inc(len(created))
    SCHEDULER_LAST_SUCCESS.set(time.time())
    if settings.worker_mode == "celery":
        _record_queue_depth()
    return {"queued": len(created), "run_ids": created}
