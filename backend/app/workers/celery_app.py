from celery import Celery

from app.core.config import settings
from app.core.observability import configure_logging

configure_logging(settings.log_level)

celery_app = Celery(
    "release_guardian",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="release_guardian",
    task_default_retry_delay=30,
    task_max_retries=3,
    task_soft_time_limit=settings.run_timeout_seconds,
    task_time_limit=settings.run_timeout_seconds + 120,
    broker_transport_options={"visibility_timeout": 3600},
    result_expires=3600,
    beat_schedule={
        "schedule-due-monitors": {
            "task": "release_guardian.schedule_due_monitors",
            "schedule": 60.0,
        },
        "sweep-stale-runs": {
            "task": "release_guardian.sweep_stale_runs",
            "schedule": 60.0,
        },
    },
)


@celery_app.task(name="release_guardian.execute_run", bind=True, max_retries=3)
def execute_run_task(self, run_id: str) -> dict:
    from app.workers.tasks.checks import execute_run

    return execute_run(run_id)


@celery_app.task(name="release_guardian.schedule_due_monitors")
def schedule_due_monitors_task() -> dict:
    from app.workers.tasks.scheduler import enqueue_due_monitors

    return enqueue_due_monitors()


@celery_app.task(name="release_guardian.sweep_stale_runs")
def sweep_stale_runs_task() -> dict:
    from app.workers.tasks.maintenance import sweep_stale_runs

    return sweep_stale_runs()