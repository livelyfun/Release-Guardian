from sqlalchemy.orm import Session

from app.models.execution import Run
from app.models.project import Monitor
from app.workers.dispatch import dispatch_run


def enqueue_runs_for_environment(
    db: Session, environment_id: str, trigger: str = "deployment"
) -> list[str]:
    monitors = (
        db.query(Monitor)
        .filter(Monitor.environment_id == environment_id, Monitor.enabled.is_(True))
        .all()
    )
    run_ids: list[str] = []
    for monitor in monitors:
        run = Run(
            monitor_id=monitor.id,
            environment_id=monitor.environment_id,
            status="pending",
            trigger=trigger,
        )
        db.add(run)
        db.flush()
        run_ids.append(run.id)
    db.commit()

    for run_id in run_ids:
        dispatch_run(run_id)
    return run_ids
