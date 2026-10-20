import json
from types import SimpleNamespace

import pytest

import app.api.v1.endpoints.runs as runs_endpoint
import app.services.checks as checks_module
from app.core.config import settings
from app.core.metrics import render_metrics
from app.services import storage
from app.services.secret_scanner import mask_secret, scan_config
from app.services.url_guard import UrlValidationError, validate_url
from tests.conftest import auth_headers, register


def _setup_monitor(client, name: str = "Homepage"):
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
        json={"name": name, "kind": "http", "target_url": "https://example.com"},
    ).json()
    return headers, workspace, monitor


def test_health_and_readiness(client):
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"


def test_metrics_endpoint_exposes_series(client):
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "# TYPE rg_api_requests_total counter" in body
    assert 'rg_api_requests_total{method="GET",route="/health",status="200"}' in body
    assert "# TYPE rg_runs_total counter" in body


def test_storage_outage_raises_controlled_error(monkeypatch):
    monkeypatch.setattr(storage, "HAS_BOTO3", False)
    with pytest.raises(storage.StorageError):
        storage.upload_bytes("run-1", "screenshot", b"png", mime_type="image/png")
    assert 'rg_artifact_uploads_total{kind="screenshot",status="failure"}' in render_metrics()


def test_lighthouse_report_parsing_and_threshold(monkeypatch):
    report = {
        "categories": {
            "performance": {"title": "Performance", "score": 0.95},
            "accessibility": {"title": "Accessibility", "score": 0.8},
        },
        "audits": {
            "largest-contentful-paint": {"numericValue": 1234.5},
            "total-blocking-time": {"numericValue": 12.0},
        },
    }

    def fake_run(cmd, **kwargs):
        output_path = next(arg.split("=", 1)[1] for arg in cmd if arg.startswith("--output-path="))
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(checks_module, "validate_url", lambda url, allow_private=False: url)
    monkeypatch.setattr("subprocess.run", fake_run)

    monitor = SimpleNamespace(
        id="m1",
        kind="lighthouse",
        target_url="https://example.com",
        config={"min_scores": {"performance": 90}},
    )
    outcome = checks_module.perform_lighthouse_check(monitor, run_id="run-1")

    assert outcome.status == "passed"
    assert outcome.summary["scores"]["performance"] == 95.0
    assert outcome.summary["performance_score"] == 95.0
    assert outcome.summary["largest_contentful_paint"] == 1234.5
    assert [step.status for step in outcome.steps] == ["passed", "passed"]


def test_lighthouse_below_threshold_fails(monkeypatch):
    report = {"categories": {"performance": {"title": "Performance", "score": 0.4}}, "audits": {}}

    def fake_run(cmd, **kwargs):
        output_path = next(arg.split("=", 1)[1] for arg in cmd if arg.startswith("--output-path="))
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(checks_module, "validate_url", lambda url, allow_private=False: url)
    monkeypatch.setattr("subprocess.run", fake_run)

    monitor = SimpleNamespace(
        id="m1",
        kind="lighthouse",
        target_url="https://example.com",
        config={"min_scores": {"performance": 90}},
    )
    outcome = checks_module.perform_lighthouse_check(monitor, run_id="run-1")

    assert outcome.status == "failed"
    assert outcome.steps[0].status == "failed"
    assert "below minimum" in outcome.steps[0].error


def test_lighthouse_missing_binary_fails_gracefully(monkeypatch):
    monkeypatch.setattr(checks_module, "validate_url", lambda url, allow_private=False: url)

    def missing_binary(*args, **kwargs):
        raise FileNotFoundError("lighthouse")

    monkeypatch.setattr("subprocess.run", missing_binary)

    monitor = SimpleNamespace(
        id="m1", kind="lighthouse", target_url="https://example.com", config={}
    )
    outcome = checks_module.perform_lighthouse_check(monitor)

    assert outcome.status == "failed"
    assert outcome.steps[0].name == "Lighthouse audit"
    assert "lighthouse" in outcome.steps[0].error


def test_url_guard_blocks_metadata_address():
    with pytest.raises(UrlValidationError):
        validate_url("http://169.254.169.254/latest/meta-data")
    assert 'rg_blocked_urls_total{reason="blocked_address"}' in render_metrics()


def test_secret_scanner_detects_and_masks():
    raw = "rg_" + "a" * 24
    findings = scan_config({"api_key": raw})
    assert findings
    assert raw not in findings[0].value
    assert mask_secret("short") == "*****"


def test_manual_trigger_rejects_duplicate_active_run(client, monkeypatch):
    headers, _workspace, monitor = _setup_monitor(client)
    monkeypatch.setattr(runs_endpoint, "dispatch_run", lambda run_id: None)
    monkeypatch.setattr(settings, "max_active_runs_per_workspace", 0)

    first = client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    assert first.status_code == 201
    assert first.json()["status"] == "pending"

    second = client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    assert second.status_code == 409
    assert "active run" in second.json()["error"]["message"]


def test_manual_trigger_enforces_workspace_capacity(client, monkeypatch):
    headers, _workspace, monitor = _setup_monitor(client, name="First")
    second_monitor = client.post(
        f"/api/v1/environments/{monitor['environment_id']}/monitors",
        headers=headers,
        json={"name": "Second", "kind": "http", "target_url": "https://example.com"},
    ).json()
    monkeypatch.setattr(runs_endpoint, "dispatch_run", lambda run_id: None)
    monkeypatch.setattr(settings, "max_active_runs_per_workspace", 1)

    first = client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    assert first.status_code == 201

    second = client.post(f"/api/v1/monitors/{second_monitor['id']}/runs", headers=headers, json={})
    assert second.status_code == 429
    assert "active-run limit" in second.json()["error"]["message"]
