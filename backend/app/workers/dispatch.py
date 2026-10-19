from app.core.config import settings


def dispatch_run(run_id: str) -> None:
    if settings.worker_mode == "inline":
        from app.workers.tasks.checks import execute_run

        execute_run(run_id)
        return

    from app.workers.celery_app import celery_app

    celery_app.send_task("release_guardian.execute_run", args=[run_id])
