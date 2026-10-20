from app.core.config import settings


def _queue_for_run(run_id: str) -> str:
    """Route heavy browser/Lighthouse work to their isolated worker queues."""
    from app.core.database import SessionLocal
    from app.models.execution import Run
    from app.models.project import Monitor

    try:
        with SessionLocal() as db:
            run = db.get(Run, run_id)
            monitor = db.get(Monitor, run.monitor_id) if run else None
            if monitor is None:
                return "release_guardian"
            if monitor.kind == "browser":
                return "browser"
            if monitor.kind == "lighthouse":
                return "lighthouse"
    except Exception:  # noqa: BLE001 - routing must never block a run
        return "release_guardian"
    return "release_guardian"


def dispatch_run(run_id: str) -> None:
    if settings.worker_mode == "inline":
        from app.workers.tasks.checks import execute_run

        execute_run(run_id)
        return

    from app.workers.celery_app import celery_app

    celery_app.send_task(
        "release_guardian.execute_run", args=[run_id], queue=_queue_for_run(run_id)
    )

