import app.services.checks as checks_module
from app.services.checks import CheckOutcome, StepOutcome
from tests.conftest import auth_headers, register


def _outcome(status: str) -> CheckOutcome:
    return CheckOutcome(
        status=status,
        duration_ms=100,
        steps=[StepOutcome(name="HTTP request", status=status, duration_ms=100)],
        summary={"status_code": 200 if status == "passed" else 500},
    )


def test_csv_exports_are_workspace_scoped(client, monkeypatch):
    headers = auth_headers(register(client)["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"workspace_id": workspace["id"], "name": "Site"},
    ).json()
    environment = client.post(
        f"/api/v1/projects/{project['id']}/environments",
        headers=headers,
        json={"name": "production", "base_url": "https://example.com"},
    ).json()
    monitor = client.post(
        f"/api/v1/environments/{environment['id']}/monitors",
        headers=headers,
        json={"name": "Homepage", "kind": "http", "target_url": "https://example.com"},
    ).json()

    monkeypatch.setattr(checks_module, "perform_http_check", lambda _monitor: _outcome("passed"))
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    runs_export = client.get(
        f"/api/v1/runs/export.csv?workspace_id={workspace['id']}", headers=headers
    )
    assert runs_export.status_code == 200
    assert runs_export.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"runs.csv\"" in runs_export.headers["content-disposition"]
    assert "id,monitor,kind,status,trigger" in runs_export.text
    assert "Homepage" in runs_export.text

    monkeypatch.setattr(checks_module, "perform_http_check", lambda _monitor: _outcome("failed"))
    client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})

    incidents_export = client.get(
        f"/api/v1/incidents/export.csv?workspace_id={workspace['id']}", headers=headers
    )
    assert incidents_export.status_code == 200
    assert "id,title,severity,status" in incidents_export.text
    assert "Homepage" in incidents_export.text

    other_headers = auth_headers(register(client, email="other@example.com")["access_token"])
    forbidden = client.get(
        f"/api/v1/runs/export.csv?workspace_id={workspace['id']}", headers=other_headers
    )
    assert forbidden.status_code == 404
