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


def test_regression_suppression_prevents_incident_until_cleared(client, monkeypatch):
    headers, workspace, monitor = _setup(client)
    monkeypatch.setattr(checks_module, "perform_http_check", _check(100))
    for _ in range(3):
        client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    suppression = client.post(
        f"/api/v1/monitors/{monitor['id']}/regression-suppression",
        headers=headers,
        json={
            "until": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "reason": "known cold start",
        },
    )
    assert suppression.status_code == 200, suppression.text
    assert suppression.json()["active"] is True
    assert suppression.json()["reason"] == "known cold start"

    monkeypatch.setattr(checks_module, "perform_http_check", _check(300))
    slow = client.post(
        f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={}
    ).json()
    assert slow["summary"]["regression"]["regression"] is True
    assert (
        slow["summary"]["regression_incident_suppressed"]["reason"]
        == "regression_suppression"
    )
    incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}", headers=headers
    ).json()
    assert incidents == []

    cleared = client.delete(
        f"/api/v1/monitors/{monitor['id']}/regression-suppression", headers=headers
    )
    assert cleared.status_code == 200
    assert cleared.json()["active"] is False

    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    incidents = client.get(
        f"/api/v1/incidents?workspace_id={workspace['id']}", headers=headers
    ).json()
    assert any("Performance regression" in incident["title"] for incident in incidents)


def test_regression_suppression_rejects_past_expiry(client):
    headers, _workspace, monitor = _setup(client)
    response = client.post(
        f"/api/v1/monitors/{monitor['id']}/regression-suppression",
        headers=headers,
        json={
            "until": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "reason": "stale",
        },
    )
    assert response.status_code == 422


def test_deployment_comparison_uses_previous_known_good(client, monkeypatch):
    headers, _workspace, monitor = _setup(client)
    environment_id = monitor["environment_id"]

    monkeypatch.setattr(checks_module, "perform_http_check", _check(100))
    first = client.post(
        f"/api/v1/environments/{environment_id}/deployments",
        headers=headers,
        json={"commit_sha": "aaaaaaa1111", "status": "success"},
    ).json()
    assert first["status"] == "passed"

    monkeypatch.setattr(checks_module, "perform_http_check", _check(300))
    second = client.post(
        f"/api/v1/environments/{environment_id}/deployments",
        headers=headers,
        json={"commit_sha": "bbbbbbb2222", "status": "success"},
    ).json()
    assert second["status"] == "passed"

    comparison = client.get(
        f"/api/v1/deployments/{second['id']}/comparison", headers=headers
    ).json()
    assert comparison["previous_known_good"]["id"] == first["id"]
    assert comparison["summary"] == {
        "regressed": 1,
        "improved": 0,
        "unchanged": 0,
        "new": 0,
        "total": 1,
    }
    current = comparison["monitors"][0]
    assert current["verdict"] == "regressed"
    assert current["current_duration_ms"] == 300
    assert current["previous_duration_ms"] == 100
    assert current["duration_delta_pct"] == 200.0
