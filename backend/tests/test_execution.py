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


def _passed(monitor):
    return CheckOutcome(
        status="passed",
        duration_ms=15,
        steps=[StepOutcome(name="HTTP request", status="passed", duration_ms=15)],
        summary={"status_code": 200},
    )


def _failed(monitor):
    return CheckOutcome(
        status="failed",
        duration_ms=15,
        steps=[
            StepOutcome(
                name="HTTP request", status="failed", duration_ms=15, error="Unexpected status 500"
            )
        ],
        summary={"status_code": 500},
    )


def test_successful_run_records_steps(client, monkeypatch):
    monkeypatch.setattr(checks_module, "perform_http_check", _passed)
    headers, workspace, monitor = _setup(client)

    response = client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["status"] == "passed"

    detail = client.get(f"/api/v1/runs/{run['id']}", headers=headers).json()
    assert len(detail["steps"]) == 1
    assert detail["steps"][0]["name"] == "HTTP request"

    incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}", headers=headers
    ).json()
    assert incidents == []


def test_failure_opens_incident_and_recovery_resolves(client, monkeypatch):
    headers, workspace, monitor = _setup(client)

    monkeypatch.setattr(checks_module, "perform_http_check", _failed)
    failed_run = client.post(
        f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={}
    ).json()
    assert failed_run["status"] == "failed"

    open_incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}&status=open", headers=headers
    ).json()
    assert len(open_incidents) == 1
    incident_id = open_incidents[0]["id"]

    monkeypatch.setattr(checks_module, "perform_http_check", _passed)
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    resolved = client.get(f"/api/v1/incidents/{incident_id}", headers=headers).json()
    assert resolved["status"] == "resolved"


def test_incident_acknowledge_transition(client, monkeypatch):
    headers, workspace, monitor = _setup(client)
    monkeypatch.setattr(checks_module, "perform_http_check", _failed)
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    incident = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}", headers=headers
    ).json()[0]
    updated = client.patch(
        f"/api/v1/incidents/{incident['id']}", headers=headers, json={"status": "acknowledged"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "acknowledged"
    assert updated.json()["acknowledged_at"] is not None


def test_deployment_registration(client):
    headers, workspace, monitor = _setup(client)
    environment_id = monitor["environment_id"]
    created = client.post(
        f"/api/v1/environments/{environment_id}/deployments",
        headers=headers,
        json={"commit_sha": "abcdef1234567890", "branch": "main", "status": "success"},
    )
    assert created.status_code == 201, created.text
    listed = client.get(
        f"/api/v1/deployments?workspace_id={workspace['id']}", headers=headers
    ).json()
    assert len(listed) == 1
