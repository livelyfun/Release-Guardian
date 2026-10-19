from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.base import utcnow
from app.models.execution import Run
from app.models.project import Monitor
from app.workers.dispatch import dispatch_run


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def enqueue_due_monitors(db: Session | None = None) -> dict:
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

    for run_id in created:
        dispatch_run(run_id)

    return {"queued": len(created), "run_ids": created}
