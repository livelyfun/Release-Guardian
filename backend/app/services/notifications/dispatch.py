import logging
import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.metrics import NOTIFICATION_ATTEMPTS
from app.models.base import utcnow
from app.models.release import (
    Incident,
    NotificationAttempt,
    NotificationChannel,
)
from app.services.notifications import Notification, build_notifier

logger = logging.getLogger("release_guardian.notifications")


def _channels(db: Session, workspace_id: str) -> list[NotificationChannel]:
    return (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.workspace_id == workspace_id,
            NotificationChannel.enabled.is_(True),
        )
        .all()
    )


def _backoff_seconds(attempts_made: int) -> float:
    """Exponential backoff with up to 25% jitter, capped by configuration."""
    base = max(1, settings.notification_retry_base_seconds)
    ceiling = max(base, settings.notification_retry_max_seconds)
    delay = min(base * (2 ** max(0, attempts_made - 1)), ceiling)
    return delay + random.uniform(0, delay * 0.25)


def _deliver(
    db: Session, attempt: NotificationAttempt, channel: NotificationChannel, severity: str
) -> None:
    """Perform one delivery and either finalize or schedule the next retry."""
    attempt.attempt += 1
    try:
        notifier = build_notifier(channel.kind, channel.config)
        notifier.send(
            Notification(
                subject=attempt.subject or "Release Guardian incident",
                body=attempt.body or "",
                severity=severity,
            )
        )
        attempt.status = "sent"
        attempt.error = None
        attempt.next_attempt_at = None
    except Exception as exc:  # noqa: BLE001 - a failed channel must not break execution
        attempt.status = "failed"
        attempt.error = str(exc)[:1000]
        if attempt.attempt >= settings.notification_max_attempts:
            attempt.next_attempt_at = None
        else:
            attempt.next_attempt_at = utcnow() + timedelta(
                seconds=_backoff_seconds(attempt.attempt)
            )
    NOTIFICATION_ATTEMPTS.inc(channel=channel.kind, status=attempt.status)


def _send(db: Session, incident: Incident, subject: str, body: str) -> None:
    for channel in _channels(db, incident.workspace_id):
        attempt = NotificationAttempt(
            channel_id=channel.id,
            incident_id=incident.id,
            status="pending",
            attempt=0,
            subject=subject,
            body=body,
        )
        db.add(attempt)
        db.flush()
        _deliver(db, attempt, channel, incident.severity)
    db.commit()


def _cancel_pending_retries(db: Session, incident: Incident) -> None:
    """Resolved incidents should not page with stale "opened" payloads."""
    db.query(NotificationAttempt).filter(
        NotificationAttempt.incident_id == incident.id,
        NotificationAttempt.status == "failed",
        NotificationAttempt.next_attempt_at.isnot(None),
    ).update(
        {
            NotificationAttempt.status: "cancelled",
            NotificationAttempt.next_attempt_at: None,
        },
        synchronize_session=False,
    )


def incident_opened(db: Session, incident: Incident) -> None:
    _send(
        db,
        incident,
        f"[{incident.severity.upper()}] {incident.title}",
        f"A new incident was opened: {incident.title}",
    )


def incident_resolved(db: Session, incident: Incident) -> None:
    _cancel_pending_retries(db, incident)
    _send(
        db,
        incident,
        f"[resolved] {incident.title}",
        f"The incident has recovered: {incident.title}",
    )


def retry_failed_notifications(db: Session | None = None) -> dict:
    """Retry deliveries whose backoff has elapsed.

    ``attempt`` counts sends, so a value of ``notification_max_attempts`` means
    the delivery is terminal. Disabled or removed channels are abandoned rather
    than retried forever.
    """
    owned = db is None
    session = db or SessionLocal()
    retried = sent = failed = abandoned = 0

    try:
        now = utcnow()
        attempts = (
            session.query(NotificationAttempt)
            .filter(
                NotificationAttempt.status == "failed",
                NotificationAttempt.next_attempt_at.isnot(None),
                NotificationAttempt.next_attempt_at <= now,
                NotificationAttempt.attempt < settings.notification_max_attempts,
            )
            .order_by(NotificationAttempt.next_attempt_at)
            .limit(settings.notification_sweep_batch)
            .all()
        )
        for attempt in attempts:
            channel = session.get(NotificationChannel, attempt.channel_id)
            if channel is None or not channel.enabled:
                attempt.status = "abandoned"
                attempt.next_attempt_at = None
                abandoned += 1
                continue

            incident = (
                session.get(Incident, attempt.incident_id) if attempt.incident_id else None
            )
            if incident is None:
                attempt.status = "abandoned"
                attempt.next_attempt_at = None
                abandoned += 1
                continue

            _deliver(session, attempt, channel, incident.severity)
            retried += 1
            if attempt.status == "sent":
                sent += 1
            else:
                failed += 1

        session.commit()
    finally:
        if owned:
            session.close()

    if abandoned:
        logger.info("notification_retries_abandoned", extra={"count": abandoned})
    return {
        "retried": retried,
        "sent": sent,
        "failed": failed,
        "abandoned": abandoned,
    }
