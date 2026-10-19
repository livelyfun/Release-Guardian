from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.execution import Run
from app.models.project import Environment, Monitor, Project
from app.models.release import Incident, IncidentEvent


def resolve_open_incidents(db: Session, dedupe_key: str) -> None:
    open_incidents = (
        db.query(Incident)
        .filter(Incident.dedupe_key == dedupe_key, Incident.status != "resolved")
        .all()
    )
    for incident in open_incidents:
        incident.status = "resolved"
        incident.resolved_at = utcnow()
        db.add(IncidentEvent(incident_id=incident.id, type="resolved", message="Check recovered"))


def open_or_refresh_incident(
    db: Session, run: Run, monitor: Monitor, environment: Environment, project: Project, reason: str
) -> Incident:
    dedupe_key = f"monitor:{monitor.id}:failure"
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
        return existing

    incident = Incident(
        workspace_id=project.workspace_id,
        project_id=project.id,
        environment_id=environment.id,
        title=f"{monitor.name} failing in {environment.name}",
        severity="high" if environment.is_production else "medium",
        dedupe_key=dedupe_key,
    )
    db.add(incident)
    db.flush()
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            type="opened",
            message=reason,
            meta={"run_id": run.id, "monitor_id": monitor.id},
        )
    )
    return incident
