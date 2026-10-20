from sqlalchemy.orm import Session

from app.models.execution import Run
from app.models.project import Monitor
from app.models.release import Deployment
from app.services.capacity import active_run_for_monitor
from app.services.github_status import post_deployment_status
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

    post_deployment_status(db, deployment)
    return deployment.status


COMPARISON_DURATION_TOLERANCE = 0.20


def _latest_runs_by_monitor(db: Session, deployment_id: str) -> dict[str, Run]:
    runs = (
        db.query(Run)
        .filter(Run.deployment_id == deployment_id)
        .order_by(Run.created_at.asc())
        .all()
    )
    latest: dict[str, Run] = {}
    for run in runs:
        latest[run.monitor_id] = run
    return latest


def build_deployment_comparison(db: Session, deployment: Deployment) -> dict:
    """Compare this deployment's checks with the last passing deployment."""
    previous = (
        db.query(Deployment)
        .filter(
            Deployment.environment_id == deployment.environment_id,
            Deployment.id != deployment.id,
            Deployment.status == "passed",
            Deployment.created_at < deployment.created_at,
        )
        .order_by(Deployment.created_at.desc())
        .first()
    )

    current_runs = _latest_runs_by_monitor(db, deployment.id)
    previous_runs = _latest_runs_by_monitor(db, previous.id) if previous else {}
    monitor_ids = set(current_runs) | set(previous_runs)
    monitors = (
        db.query(Monitor).filter(Monitor.id.in_(monitor_ids)).all() if monitor_ids else []
    )
    name_map = {monitor.id: monitor.name for monitor in monitors}

    comparisons = []
    summary = {"regressed": 0, "improved": 0, "unchanged": 0, "new": 0, "total": 0}
    for monitor_id in sorted(monitor_ids, key=lambda value: name_map.get(value, value)):
        current = current_runs.get(monitor_id)
        prior = previous_runs.get(monitor_id)
        duration_delta = None
        if (
            current is not None
            and prior is not None
            and current.duration_ms is not None
            and prior.duration_ms
        ):
            duration_delta = round(
                (current.duration_ms - prior.duration_ms) / prior.duration_ms * 100, 1
            )

        if prior is None:
            verdict = "new"
        elif current is None:
            verdict = "unchanged"
        else:
            current_failed = current.status in {"failed", "inconclusive"}
            previous_passed = prior.status == "passed"
            regressed = (current_failed and previous_passed) or (
                current.status == "passed"
                and previous_passed
                and duration_delta is not None
                and duration_delta > COMPARISON_DURATION_TOLERANCE * 100
            )
            improved = (
                current.status == "passed" and not previous_passed
            ) or (
                current.status == "passed"
                and previous_passed
                and duration_delta is not None
                and duration_delta < -(COMPARISON_DURATION_TOLERANCE * 100)
            )
            verdict = "regressed" if regressed else "improved" if improved else "unchanged"

        summary[verdict] += 1
        summary["total"] += 1
        comparisons.append(
            {
                "monitor_id": monitor_id,
                "monitor_name": name_map.get(monitor_id, monitor_id[:8]),
                "current_status": current.status if current else None,
                "previous_status": prior.status if prior else None,
                "current_duration_ms": current.duration_ms if current else None,
                "previous_duration_ms": prior.duration_ms if prior else None,
                "duration_delta_pct": duration_delta,
                "verdict": verdict,
            }
        )

    return {
        "deployment_id": deployment.id,
        "status": deployment.status,
        "previous_known_good": previous,
        "monitors": comparisons,
        "summary": summary,
    }
