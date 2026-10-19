import app.services.checks as checks_module
from app.services.checks import CheckOutcome, StepOutcome
from app.workers.tasks.scheduler import enqueue_due_monitors
from tests.conftest import auth_headers, register


def _passed(monitor):
    return CheckOutcome(
        status="passed",
        duration_ms=10,
        steps=[StepOutcome(name="HTTP request", status="passed", duration_ms=10)],
        summary={"status_code": 200},
    )


def _setup(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
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
        json={
            "name": "Homepage",
            "kind": "http",
            "target_url": "https://example.com",
            "interval_seconds": 60,
        },
    ).json()
    return headers, workspace, environment, monitor


def test_scheduler_enqueues_once_then_respects_interval(client, monkeypatch):
    monkeypatch.setattr(checks_module, "perform_http_check", _passed)
    headers, _, _, monitor = _setup(client)

    first = enqueue_due_monitors()
    assert first["queued"] == 1

    runs = client.get(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers).json()
    assert len(runs) == 1
    assert runs[0]["trigger"] == "scheduled"

    second = enqueue_due_monitors()
    assert second["queued"] == 0


def test_scheduler_skips_disabled_monitors(client, monkeypatch):
    monkeypatch.setattr(checks_module, "perform_http_check", _passed)
    headers, _, _, monitor = _setup(client)
    client.patch(f"/api/v1/monitors/{monitor['id']}", headers=headers, json={"enabled": False})

    result = enqueue_due_monitors()
    assert result["queued"] == 0


def test_deployment_triggers_environment_runs(client, monkeypatch):
    monkeypatch.setattr(checks_module, "perform_http_check", _passed)
    headers, workspace, environment, monitor = _setup(client)

    created = client.post(
        f"/api/v1/environments/{environment['id']}/deployments",
        headers=headers,
        json={"commit_sha": "abcdef1234567890", "branch": "main", "status": "success"},
    )
    assert created.status_code == 201, created.text

    runs = client.get(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers).json()
    assert len(runs) == 1
    assert runs[0]["trigger"] == "deployment"
    assert runs[0]["status"] == "passed"
