from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.execution import Run, EscalationRule
from app.models.project import Environment, Monitor, Project
from app.models.release import Incident, IncidentEvent
from app.services.notifications import dispatch as notification_dispatch


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


def _escalate_incident(db: Session, incident: Incident) -> Incident | None:
    """Move an incident to its next escalation level based on rules and time elapsed."""
    rule = (
        db.query(EscalationRule)
        .filter(EscalationRule.workspace_id == incident.workspace_id, EscalationRule.severity == incident.severity, EscalationRule.is_enabled.is_(True))
        .order_by(EscalationRule.minutes_to_escalate.asc())
        .first()
    )
    if rule is None:
        return None

    # Check if enough time has elapsed since the last escalation
    last_escalation = (
        db.query(IncidentEvent)
        .filter(IncidentEvent.incident_id == incident.id, IncidentEvent.type == "escalated")
        .order_by(IncidentEvent.created_at.desc())
        .first()
    )

    if last_escalation:
        elapsed_minutes = (utcnow() - last_escalation.created_at).total_seconds() / 60
        if elapsed_minutes < rule.minutes_to_escalate:
            return incident  # Not yet time for next escalation

    # Create escalation event
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            type="escalated",
            message=f"Escalated to {rule.channel_kind} (configured after {rule.minutes_to_escalate} minutes)",
            meta={"escalation_rule_id": rule.id, "minutes_to_escalate": rule.minutes_to_escalate},
        )
    )

    # Dispatch notification via the configured channel
    try:
        if rule.channel_kind == "webhook":
            from app.services.notifications.webhook import WebhookNotifier
            url = rule.channel_config_key or ""
            if url:
                notifier = WebhookNotifier(url)
                notifier.send(
                    subject=f"[{incident.severity.upper()}] Escalated incident: {incident.title}",
                    body=f"Incident has been escalated: {incident.title}\n\nReason: {incident.dedupe_key}\n\nIncident ID: {incident.id}",
                    severity=incident.severity,
                )
        elif rule.channel_kind == "email":
            from app.services.notifications.email import EmailNotifier
            to = rule.channel_config_key or ""
            if to:
                notifier = EmailNotifier(config={"to": to})
                notifier.send(
                    subject=f"[{incident.severity.upper()}] Escalated incident: {incident.title}",
                    body=f"Incident has been escalated: {incident.title}\n\nReason: {incident.dedupe_key}\n\nIncident ID: {incident.id}",
                    severity=incident.severity,
                )
    except Exception as exc:  # noqa: BLE001 - non-fatal if escalation fails
        incident.escalation_error = str(exc)[:200]

    db.commit()
    return incident


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