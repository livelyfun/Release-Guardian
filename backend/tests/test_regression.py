import app.workers.tasks.checks as checks_module
from app.services.checks import CheckOutcome, StepOutcome
from tests.conftest import auth_headers, register


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
        json={"name": "Homepage", "kind": "http", "target_url": "https://example.com"},
    ).json()
    return headers, workspace, monitor


def _check(duration):
    def run(monitor):
        return CheckOutcome(
            status="passed",
            duration_ms=duration,
            steps=[StepOutcome(name="HTTP request", status="passed", duration_ms=duration)],
            summary={"status_code": 200},
        )

    return run


def test_performance_regression_detected_after_baseline(client, monkeypatch):
    headers, workspace, monitor = _setup(client)

    monkeypatch.setattr(checks_module, "perform_http_check", _check(100))
    for _ in range(3):
        response = client.post(
            f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={}
        )
        assert response.json()["status"] == "passed"

    monkeypatch.setattr(checks_module, "perform_http_check", _check(300))
    slow_run = client.post(
        f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={}
    ).json()

    assert slow_run["summary"]["regression"]["regression"] is True
    assert slow_run["summary"]["regression"]["baseline_ms"] == 100.0

    incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}", headers=headers
    ).json()
    titles = [incident["title"] for incident in incidents]
    assert any("Performance regression" in title for title in titles)


def test_no_regression_incident_for_stable_durations(client, monkeypatch):
    headers, workspace, monitor = _setup(client)
    monkeypatch.setattr(checks_module, "perform_http_check", _check(120))
    for _ in range(4):
        client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}", headers=headers
    ).json()
    assert incidents == []
