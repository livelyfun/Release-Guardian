from datetime import timedelta

import app.services.checks as checks_module
import app.services.notifications.dispatch as dispatch_module
from app.core.config import settings
from app.models.base import utcnow
from app.models.release import NotificationAttempt, NotificationChannel
from app.services.checks import CheckOutcome, StepOutcome
from app.services.notifications.dispatch import retry_failed_notifications
from tests.conftest import auth_headers, register


class _FakeNotifier:
    kind = "webhook"

    def __init__(self) -> None:
        self.sent = []

    def send(self, notification) -> None:
        self.sent.append(notification)


def _failed(monitor):
    return CheckOutcome(
        status="failed",
        duration_ms=10,
        steps=[StepOutcome(name="HTTP request", status="failed", duration_ms=10, error="boom")],
        summary={"status_code": 500},
    )


def _setup(client, db):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    db.add(
        NotificationChannel(
            workspace_id=workspace["id"], kind="webhook", config={"url": "https://hooks.example/x"}
        )
    )
    db.commit()

    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"workspace_id": workspace["id"], "name": "Site"},
    ).json()
    environment = client.post(
        f"/api/v1/projects/{project['id']}/environments",
        headers=headers,
        json={"name": "production", "base_url": "https://example.com", "is_production": True},
    ).json()
    monitor = client.post(
        f"/api/v1/environments/{environment['id']}/monitors",
        headers=headers,
        json={"name": "Homepage", "kind": "http", "target_url": "https://example.com"},
    ).json()
    return headers, workspace, monitor


def test_incident_open_sends_notification(client, db, monkeypatch):
    fake = _FakeNotifier()
    monkeypatch.setattr(dispatch_module, "build_notifier", lambda kind, config: fake)
    monkeypatch.setattr(checks_module, "perform_http_check", _failed)

    headers, workspace, monitor = _setup(client, db)
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    assert len(fake.sent) == 1
    attempts = db.query(NotificationAttempt).all()
    assert len(attempts) == 1
    assert attempts[0].status == "sent"


class _FlakyNotifier:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0
        self.sent = []

    def send(self, notification) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("provider unavailable")
        self.sent.append(notification)


def test_failed_notification_retries_after_backoff(client, db, monkeypatch):
    monkeypatch.setattr(settings, "notification_max_attempts", 3)
    monkeypatch.setattr(settings, "notification_retry_base_seconds", 30)
    monkeypatch.setattr(settings, "notification_retry_max_seconds", 60)

    flaky = _FlakyNotifier(failures=1)
    monkeypatch.setattr(dispatch_module, "build_notifier", lambda kind, config: flaky)
    monkeypatch.setattr(checks_module, "perform_http_check", _failed)

    headers, workspace, monitor = _setup(client, db)
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    attempt = db.query(NotificationAttempt).one()
    assert attempt.status == "failed"
    assert attempt.attempt == 1
    assert attempt.next_attempt_at is not None
    assert attempt.subject and attempt.body

    # Backoff has not elapsed yet.
    assert retry_failed_notifications()["retried"] == 0

    attempt.next_attempt_at = utcnow() - timedelta(seconds=1)
    db.commit()

    result = retry_failed_notifications()
    assert result == {"retried": 1, "sent": 1, "failed": 0, "abandoned": 0}
    db.refresh(attempt)
    assert attempt.status == "sent"
    assert attempt.attempt == 2
    assert attempt.next_attempt_at is None
    assert len(flaky.sent) == 1


def test_notification_retries_stop_at_max_attempts(client, db, monkeypatch):
    monkeypatch.setattr(settings, "notification_max_attempts", 2)
    monkeypatch.setattr(settings, "notification_retry_base_seconds", 1)
    monkeypatch.setattr(settings, "notification_retry_max_seconds", 1)

    flaky = _FlakyNotifier(failures=99)
    monkeypatch.setattr(dispatch_module, "build_notifier", lambda kind, config: flaky)
    monkeypatch.setattr(checks_module, "perform_http_check", _failed)

    headers, workspace, monitor = _setup(client, db)
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    attempt = db.query(NotificationAttempt).one()
    attempt.next_attempt_at = utcnow() - timedelta(seconds=1)
    db.commit()

    result = retry_failed_notifications()
    assert result["failed"] == 1
    db.refresh(attempt)
    assert attempt.status == "failed"
    assert attempt.attempt == 2
    assert attempt.next_attempt_at is None

    # No further retries are scheduled.
    assert retry_failed_notifications()["retried"] == 0


def test_resolving_incident_cancels_pending_retries(client, db, monkeypatch):
    monkeypatch.setattr(settings, "notification_max_attempts", 3)
    monkeypatch.setattr(settings, "notification_retry_base_seconds", 30)

    failing = _FlakyNotifier(failures=99)
    monkeypatch.setattr(dispatch_module, "build_notifier", lambda kind, config: failing)
    monkeypatch.setattr(checks_module, "perform_http_check", _failed)

    headers, workspace, monitor = _setup(client, db)
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    healthy = _FlakyNotifier(failures=0)
    monkeypatch.setattr(dispatch_module, "build_notifier", lambda kind, config: healthy)
    monkeypatch.setattr(
        checks_module,
        "perform_http_check",
        lambda monitor: CheckOutcome(
            status="passed",
            duration_ms=5,
            steps=[StepOutcome(name="HTTP request", status="passed", duration_ms=5)],
            summary={"status_code": 200},
        ),
    )
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    attempts = db.query(NotificationAttempt).order_by(NotificationAttempt.created_at).all()
    assert attempts[0].status == "cancelled"
    assert attempts[0].next_attempt_at is None
    assert attempts[1].status == "sent"
    assert len(healthy.sent) == 1
