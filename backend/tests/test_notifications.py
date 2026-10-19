import app.services.notifications.dispatch as dispatch_module
import app.workers.tasks.checks as checks_module
from app.models.release import NotificationAttempt, NotificationChannel
from app.services.checks import CheckOutcome, StepOutcome
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
