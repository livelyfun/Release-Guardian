from sqlalchemy.orm import Session

from app.models.execution import Run
from app.models.project import Monitor
from app.models.release import Deployment
from app.services.capacity import active_run_for_monitor
from app.workers.dispatch import dispatch_run


def enqueue_runs_for_environment(
    db: Session,
    environment_id: str,
    trigger: str = "deployment",
    deployment_id: str | None = None,
) -> list[str]:
    monitors = (
        db.query(Monitor)
        .filter(Monitor.environment_id == environment_id, Monitor.enabled.is_(True))
        .all()
    )
    run_ids: list[str] = []
    for monitor in monitors:
        # Backpressure: do not stack deployment runs behind an in-flight check
        # for the same monitor.  The in-flight run already represents current
        # state for that target.
        if active_run_for_monitor(db, monitor.id) is not None:
            continue
        run = Run(
            monitor_id=monitor.id,
            environment_id=monitor.environment_id,
            deployment_id=deployment_id,
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


def refresh_deployment_status(db: Session, deployment_id: str) -> str | None:
    deployment = db.get(Deployment, deployment_id)
    if deployment is None:
        return None

    statuses = [
        status
        for (status,) in db.query(Run.status).filter(Run.deployment_id == deployment_id).all()
    ]

    if not statuses:
        deployment.status = "inconclusive"
    elif any(status in {"pending", "running"} for status in statuses):
        deployment.status = "pending"
    elif "failed" in statuses:
        deployment.status = "failed"
    elif "inconclusive" in statuses:
        deployment.status = "inconclusive"
    else:
        deployment.status = "passed"

    return deployment.status
