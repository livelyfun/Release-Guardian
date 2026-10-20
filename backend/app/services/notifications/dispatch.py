from sqlalchemy.orm import Session

from app.core.metrics import NOTIFICATION_ATTEMPTS
from app.models.release import Incident, NotificationAttempt, NotificationChannel
from app.services.notifications import Notification, build_notifier


def _channels(db: Session, workspace_id: str) -> list[NotificationChannel]:
    return (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.workspace_id == workspace_id,
            NotificationChannel.enabled.is_(True),
        )
        .all()
    )


def _send(db: Session, incident: Incident, subject: str, body: str) -> None:
    for channel in _channels(db, incident.workspace_id):
        attempt = NotificationAttempt(
            channel_id=channel.id,
            incident_id=incident.id,
            status="pending",
        )
        db.add(attempt)
        db.flush()
        try:
            notifier = build_notifier(channel.kind, channel.config)
            notifier.send(Notification(subject=subject, body=body, severity=incident.severity))
            attempt.status = "sent"
        except Exception as exc:  # noqa: BLE001 - a failed channel must not break execution
            attempt.status = "failed"
            attempt.error = str(exc)[:1000]
        NOTIFICATION_ATTEMPTS.inc(channel=channel.kind, status=attempt.status)
    db.commit()


def incident_opened(db: Session, incident: Incident) -> None:
    _send(
        db,
        incident,
        f"[{incident.severity.upper()}] {incident.title}",
        f"A new incident was opened: {incident.title}",
    )


def incident_resolved(db: Session, incident: Incident) -> None:
    _send(
        db,
        incident,
        f"[resolved] {incident.title}",
        f"The incident has recovered: {incident.title}",
    )
