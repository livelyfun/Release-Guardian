from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.metrics import ESCALATIONS
from app.models.base import utcnow
from app.models.execution import EscalationRule, Run
from app.models.project import Environment, Monitor, Project
from app.models.release import Incident, IncidentEvent
from app.services.notifications import Notification, build_notifier


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def failure_threshold(monitor) -> int:
    """Consecutive failed runs required before opening an incident (1-10)."""
    raw = (monitor.config or {}).get("consecutive_failures", 1)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    return min(max(value, 1), 10)


def failure_threshold_reached(db: Session, run: Run, threshold: int) -> bool:
    """Count the current run plus immediately preceding runs for this monitor."""
    if threshold <= 1:
        return True

    recent = (
        db.query(Run.status)
        .filter(
            Run.monitor_id == run.monitor_id,
            Run.id != run.id,
            Run.status.in_(["passed", "failed"]),
        )
        .order_by(Run.created_at.desc())
        .limit(threshold - 1)
        .all()
    )
    failures = 1
    for (status,) in recent:
        if status != "failed":
            break
        failures += 1
    return failures >= threshold


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


def escalate_due_incidents(db: Session | None = None) -> dict:
    """Fire every escalation rule whose threshold has elapsed.

    Rules form a ladder: each rule fires at most once per incident.  Failed
    deliveries are recorded as ``escalation_failed`` events and retried on the
    next sweep; successful rules are never re-sent.  Resolved incidents are
    ignored, so recovery stops paging.
    """
    owned = db is None
    session = db or SessionLocal()
    escalated: list[str] = []
    failed: list[str] = []

    try:
        now = utcnow()
        incidents = (
            session.query(Incident)
            .filter(Incident.status.in_(["open", "acknowledged"]))
            .order_by(Incident.opened_at)
            .limit(settings.escalation_sweep_batch)
            .all()
        )
        for incident in incidents:
            rules = (
                session.query(EscalationRule)
                .filter(
                    EscalationRule.workspace_id == incident.workspace_id,
                    EscalationRule.severity == incident.severity,
                    EscalationRule.is_enabled.is_(True),
                )
                .order_by(EscalationRule.minutes_to_escalate)
                .all()
            )
            if not rules:
                continue

            fired = {
                (event.meta or {}).get("escalation_rule_id")
                for event in session.query(IncidentEvent)
                .filter(
                    IncidentEvent.incident_id == incident.id,
                    IncidentEvent.type == "escalated",
                )
                .all()
            }
            opened_at = _as_utc(incident.opened_at)
            elapsed_minutes = (now - opened_at).total_seconds() / 60

            for rule in rules:
                if rule.id in fired or elapsed_minutes < rule.minutes_to_escalate:
                    continue

                subject = f"[{incident.severity.upper()}] Escalated incident: {incident.title}"
                body = (
                    f"Incident escalated after {rule.minutes_to_escalate} minutes.\n\n"
                    f"Incident: {incident.title}\n"
                    f"Key: {incident.dedupe_key}\n"
                    f"Rule: {rule.name} ({rule.channel_kind})\n"
                    f"Incident ID: {incident.id}"
                )
                error: str | None = None
                try:
                    notifier = build_notifier(rule.channel_kind, rule.channel_config)
                    notifier.send(
                        Notification(
                            subject=subject, body=body, severity=incident.severity
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - one channel must not stop the ladder
                    error = str(exc)[:500]
                    failed.append(rule.id)
                    ESCALATIONS.inc(status="failed")
                    session.add(
                        IncidentEvent(
                            incident_id=incident.id,
                            type="escalation_failed",
                            message=f"Escalation to {rule.channel_kind} failed: {error}",
                            meta={
                                "escalation_rule_id": rule.id,
                                "channel_kind": rule.channel_kind,
                            },
                        )
                    )
                    continue

                ESCALATIONS.inc(status="sent")
                escalated.append(rule.id)
                session.add(
                    IncidentEvent(
                        incident_id=incident.id,
                        type="escalated",
                        message=(
                            f"Escalated via {rule.channel_kind} after "
                            f"{rule.minutes_to_escalate} minutes ({rule.name})"
                        ),
                        meta={
                            "escalation_rule_id": rule.id,
                            "channel_kind": rule.channel_kind,
                            "minutes_to_escalate": rule.minutes_to_escalate,
                        },
                    )
                )

        session.commit()
    finally:
        if owned:
            session.close()

    return {"escalated": escalated, "failed": failed}


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