from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.execution import Run
from app.models.project import Environment, Monitor, Project
from app.models.release import Incident, IncidentEvent


def resolve_open_incidents(db: Session, dedupe_key: str) -> list[Incident]:
    open_incidents = (
        db.query(Incident)
        .filter(Incident.dedupe_key == dedupe_key, Incident.status != "resolved")
        .all()
    )
    for incident in open_incidents:
        incident.status = "resolved"
        incident.resolved_at = utcnow()
        db.add(IncidentEvent(incident_id=incident.id, type="resolved", message="Check recovered"))
    return open_incidents


def _open_or_refresh(
    db: Session,
    *,
    dedupe_key: str,
    title: str,
    severity: str,
    run: Run,
    project: Project,
    environment: Environment,
    reason: str,
) -> tuple[Incident, bool]:
    existing = (
        db.query(Incident)
        .filter(Incident.dedupe_key == dedupe_key, Incident.status != "resolved")
        .order_by(Incident.opened_at.desc())
        .first()
    )
    if existing is not None:
        db.add(
            IncidentEvent(
                incident_id=existing.id,
                type="recurrence",
                message=reason,
                meta={"run_id": run.id},
            )
        )
        return existing, False

    incident = Incident(
        workspace_id=project.workspace_id,
        project_id=project.id,
        environment_id=environment.id,
        title=title,
        severity=severity,
        dedupe_key=dedupe_key,
    )
    db.add(incident)
    db.flush()
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            type="opened",
            message=reason,
            meta={"run_id": run.id},
        )
    )
    return incident, True


def open_or_refresh_incident(
    db: Session, run: Run, monitor: Monitor, environment: Environment, project: Project, reason: str
) -> tuple[Incident, bool]:
    return _open_or_refresh(
        db,
        dedupe_key=f"monitor:{monitor.id}:failure",
        title=f"{monitor.name} failing in {environment.name}",
        severity="high" if environment.is_production else "medium",
        run=run,
        project=project,
        environment=environment,
        reason=reason,
    )


def open_regression_incident(
    db: Session,
    run: Run,
    monitor: Monitor,
    environment: Environment,
    project: Project,
    actual_ms: int,
    baseline_ms: float,
    threshold_ms: float,
) -> tuple[Incident, bool]:
    reason = (
        f"Duration {actual_ms} ms exceeded baseline {baseline_ms:.0f} ms "
        f"(threshold {threshold_ms:.0f} ms)"
    )
    return _open_or_refresh(
        db,
        dedupe_key=f"monitor:{monitor.id}:regression",
        title=f"Performance regression: {monitor.name} in {environment.name}",
        severity="medium" if environment.is_production else "low",
        run=run,
        project=project,
        environment=environment,
        reason=reason,
    )
