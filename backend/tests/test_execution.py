from datetime import UTC, datetime, timedelta

import app.services.checks as checks_module
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


def test_consecutive_failure_threshold_delays_incident(client, monkeypatch):
    headers, workspace, monitor = _setup(client)
    updated = client.patch(
        f"/api/v1/monitors/{monitor['id']}",
        headers=headers,
        json={"config": {"consecutive_failures": 3}},
    )
    assert updated.status_code == 200

    monkeypatch.setattr(checks_module, "perform_http_check", _failed)
    for expected in (0, 0, 1):
        run = client.post(
            f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={}
        ).json()
        assert run["status"] == "failed"
        incidents = client.get(
            f"/api/v1/incidents?workspace_id={workspace['id']}&status=open",
            headers=headers,
        ).json()
        assert len(incidents) == expected

    monkeypatch.setattr(checks_module, "perform_http_check", _passed)
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}&status=open", headers=headers
    ).json()
    assert incidents == []


def test_maintenance_window_suppresses_incident(client, monkeypatch):
    headers, workspace, monitor = _setup(client)
    now = datetime.now(UTC)
    payload = {
        "reason": "planned deploy",
        "starts_at": (now - timedelta(minutes=1)).isoformat(),
        "ends_at": (now + timedelta(hours=1)).isoformat(),
    }
    created = client.post(
        f"/api/v1/workspaces/{workspace['id']}/maintenance-windows",
        headers=headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    window_id = created.json()["id"]

    active = client.get(
        f"/api/v1/workspaces/{workspace['id']}/maintenance-windows?active_only=true",
        headers=headers,
    ).json()
    assert [window["id"] for window in active] == [window_id]

    monkeypatch.setattr(checks_module, "perform_http_check", _failed)
    run = client.post(
        f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={}
    ).json()
    detail = client.get(f"/api/v1/runs/{run['id']}", headers=headers).json()
    assert detail["summary"]["maintenance_window"]["id"] == window_id
    assert detail["summary"]["incident_suppressed"] == "maintenance_window"

    incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}", headers=headers
    ).json()
    assert incidents == []

    deleted = client.delete(
        f"/api/v1/maintenance-windows/{window_id}", headers=headers
    )
    assert deleted.status_code == 204

    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}&status=open", headers=headers
    ).json()
    assert len(incidents) == 1


def test_maintenance_window_validation(client):
    headers, workspace, monitor = _setup(client)
    now = datetime.now(UTC)
    two_scopes = client.post(
        f"/api/v1/workspaces/{workspace['id']}/maintenance-windows",
        headers=headers,
        json={
            "project_id": "one",
            "monitor_id": monitor["id"],
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(minutes=5)).isoformat(),
        },
    )
    assert two_scopes.status_code == 422

    backwards = client.post(
        f"/api/v1/workspaces/{workspace['id']}/maintenance-windows",
        headers=headers,
        json={
            "starts_at": (now + timedelta(minutes=5)).isoformat(),
            "ends_at": now.isoformat(),
        },
    )
    assert backwards.status_code == 422


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
