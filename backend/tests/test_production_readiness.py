import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

import app.api.v1.endpoints.artifacts as artifacts_endpoint
import app.api.v1.endpoints.runs as runs_endpoint
import app.services.checks as checks_module
import app.services.incidents as incidents_module
import app.workers.tasks.checks as worker_checks
from app.core.config import Settings, settings
from app.core.database import SessionLocal
from app.core.metrics import render_metrics
from app.core.production import production_config_issues
from app.core.rate_limit import _use_redis
from app.core.security import sign_webhook, verify_webhook_signature
from app.models.base import utcnow
from app.models.execution import Artifact, Run
from app.models.project import Environment
from app.models.release import Incident, IncidentEvent
from app.services import locks, storage
from app.services.incidents import escalate_due_incidents
from app.services.secret_scanner import mask_secret, scan_config
from app.services.url_guard import UrlValidationError, validate_url
from app.workers.tasks import maintenance
from app.workers.tasks import scheduler as scheduler_module
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


def test_metrics_token_protects_endpoint(client, monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "scrape-token")
    assert client.get("/metrics").status_code == 404
    authorized = client.get("/metrics", headers={"Authorization": "Bearer scrape-token"})
    assert authorized.status_code == 200
    assert "rg_api_requests_total" in authorized.text


def test_artifact_signed_url_requires_workspace_ownership(client, monkeypatch):
    headers, workspace, monitor = _setup_monitor(client)
    created = client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    assert created.status_code == 201
    run_id = created.json()["id"]
    storage_key = f"artifacts/{run_id}/screenshot-abc123"

    db = SessionLocal()
    try:
        db.add(
            Artifact(
                run_id=run_id,
                kind="screenshot",
                storage_key=storage_key,
                url="https://example.com/expired",
                size_bytes=10,
                mime_type="image/png",
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(
        artifacts_endpoint, "get_signed_url", lambda key: f"https://signed.example/{key}"
    )

    same_workspace = client.get(
        f"/api/v1/workspaces/{workspace['id']}/artifacts/signed-url",
        headers=headers,
        params={"artifact_key": storage_key},
    )
    assert same_workspace.status_code == 200
    assert same_workspace.json()["expires_in_seconds"] == settings.artifact_url_ttl_seconds

    other = register(client, email="other@example.com")
    other_headers = auth_headers(other["access_token"])
    other_workspace = client.get("/api/v1/workspaces", headers=other_headers).json()[0]

    cross_tenant = client.get(
        f"/api/v1/workspaces/{other_workspace['id']}/artifacts/signed-url",
        headers=other_headers,
        params={"artifact_key": storage_key},
    )
    assert cross_tenant.status_code == 404

    missing = client.get(
        f"/api/v1/workspaces/{workspace['id']}/artifacts/signed-url",
        headers=headers,
        params={"artifact_key": "artifacts/nope/none"},
    )
    assert missing.status_code == 404


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


def test_secret_scanner_ignores_infrastructure_ids():
    findings = scan_config(
        {
            "SHELL_SESSION_ID": "0123456789abcdef0123456789abcdef",
            "INVOCATION_ID": "fedcba9876543210fedcba9876543210",
        }
    )
    assert findings == []


def test_webhook_signature_roundtrip_and_tamper_detection():
    body = b'{"subject":"incident"}'
    timestamp = "1790000000"
    signature = sign_webhook(body, timestamp)
    assert verify_webhook_signature(body, timestamp, signature) is True
    assert verify_webhook_signature(body + b" ", timestamp, signature) is False
    assert verify_webhook_signature(body, "1790000001", signature) is False


def test_production_config_guard_flags_defaults():
    unsafe = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="change-me-in-production",
        webhook_signing_secret="change-me-webhook-secret",
        database_url="sqlite://",
        allow_private_urls=True,
        cors_origins=["*"],
    )
    issues = production_config_issues(unsafe)
    text = " ".join(issues)
    assert "JWT_SECRET" in text
    assert "WEBHOOK_SIGNING_SECRET" in text
    assert "SQLite" in text
    assert "ALLOW_PRIVATE_URLS" in text
    assert "CORS_ORIGINS" in text


def test_production_config_guard_accepts_hardened_config():
    safe = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="a" * 48,
        webhook_signing_secret="b" * 32,
        database_url="postgresql+psycopg://user:pass@db:5432/rg",
        allow_private_urls=False,
        cors_origins=["https://app.example.com"],
        worker_mode="celery",
    )
    assert production_config_issues(safe) == []


def test_rate_limit_backend_selection(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_backend", "memory")
    assert _use_redis() is False
    monkeypatch.setattr(settings, "rate_limit_backend", "auto")
    monkeypatch.setattr(settings, "worker_mode", "celery")
    assert _use_redis() is True
    monkeypatch.setattr(settings, "worker_mode", "inline")
    assert _use_redis() is False


def test_scheduler_skips_when_lock_held(monkeypatch):
    calls = []
    monkeypatch.setattr(
        scheduler_module,
        "acquire_scheduler_lock",
        lambda: (False, None),
    )
    monkeypatch.setattr(scheduler_module, "dispatch_run", lambda run_id: calls.append(run_id))

    result = scheduler_module.enqueue_due_monitors()

    assert result == {"queued": 0, "run_ids": [], "skipped": "lock_held"}
    assert calls == []


def test_scheduler_lock_falls_back_when_redis_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "worker_mode", "celery")

    def unavailable():
        raise ConnectionError("redis down")

    monkeypatch.setattr(locks, "_client", unavailable)
    acquired, token = locks.acquire_scheduler_lock()
    assert acquired is True
    assert token is None


def test_deployment_skips_monitor_with_active_run(client, monkeypatch):
    headers, _workspace, monitor = _setup_monitor(client)
    monkeypatch.setattr(runs_endpoint, "dispatch_run", lambda run_id: None)
    monkeypatch.setattr(settings, "max_active_runs_per_workspace", 0)

    manual = client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    assert manual.status_code == 201

    deployment = client.post(
        f"/api/v1/environments/{monitor['environment_id']}/deployments",
        headers=headers,
        json={"commit_sha": "abcdef1234567890", "branch": "main", "status": "success"},
    )
    assert deployment.status_code == 201
    assert deployment.json()["status"] == "inconclusive"

    runs = client.get(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers).json()
    assert len(runs) == 1


def test_sweeper_redispatches_old_pending_runs(client, monkeypatch):
    _headers, _workspace, monitor = _setup_monitor(client)
    db = SessionLocal()
    try:
        run = Run(
            monitor_id=monitor["id"],
            environment_id=monitor["environment_id"],
            status="pending",
            trigger="manual",
        )
        db.add(run)
        db.commit()
        run.created_at = utcnow() - timedelta(seconds=settings.pending_run_timeout_seconds + 60)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    dispatched = []
    monkeypatch.setattr(maintenance, "dispatch_run", lambda run_id: dispatched.append(run_id))
    result = maintenance.sweep_stale_runs()

    assert result["redispatched"] == [run_id]
    assert dispatched == [run_id]


def test_sweeper_times_out_stuck_running_run(client):
    _headers, _workspace, monitor = _setup_monitor(client)
    db = SessionLocal()
    try:
        run = Run(
            monitor_id=monitor["id"],
            environment_id=monitor["environment_id"],
            status="running",
            trigger="manual",
            started_at=utcnow() - timedelta(seconds=settings.run_timeout_seconds + 120),
        )
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    result = maintenance.sweep_stale_runs()
    assert result["timed_out"] == [run_id]

    db = SessionLocal()
    try:
        refreshed = db.get(Run, run_id)
        assert refreshed.status == "inconclusive"
        assert "exceeded" in refreshed.summary["error"]
    finally:
        db.close()


def test_execute_run_skips_terminal_run(client, monkeypatch):
    headers, _workspace, monitor = _setup_monitor(client)
    created = client.post(f"/api/v1/monitors/{monitor['id']}/runs", headers=headers, json={})
    assert created.status_code == 201
    run_id = created.json()["id"]

    def must_not_execute(monitor, run_id=None):
        raise AssertionError("terminal run was executed again")

    monkeypatch.setattr(checks_module, "perform_http_check", must_not_execute)
    result = worker_checks.execute_run(run_id)
    assert result["skipped"] == "terminal"


def test_execute_run_ignores_duplicate_lock(monkeypatch):
    monkeypatch.setattr(worker_checks, "acquire_run_lock", lambda run_id: (False, None))
    result = worker_checks.execute_run("run-does-not-matter")
    assert result["status"] == "duplicate"


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


class _RecordingNotifier:
    def __init__(self, sent: list):
        self.sent = sent

    def send(self, notification) -> None:
        self.sent.append(notification)


class _BrokenNotifier:
    def send(self, notification) -> None:
        raise RuntimeError("provider unavailable")


def _make_incident(db, workspace: dict, monitor: dict, *, severity: str, minutes_old: int) -> str:
    environment = db.get(Environment, monitor["environment_id"])
    incident = Incident(
        workspace_id=workspace["id"],
        project_id=environment.project_id,
        environment_id=environment.id,
        title="Escalation test incident",
        severity=severity,
        dedupe_key=f"test:{severity}:{utcnow().timestamp()}",
        opened_at=utcnow() - timedelta(minutes=minutes_old),
    )
    db.add(incident)
    db.commit()
    return incident.id


def test_escalation_ladder_fires_once_and_matches_severity(client, monkeypatch):
    headers, workspace, monitor = _setup_monitor(client)

    for name, minutes in (("page-oncall", 5), ("page-manager", 10)):
        response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/escalation-rules",
            headers=headers,
            json={
                "name": name,
                "severity": "high",
                "minutes_to_escalate": minutes,
                "kind": "webhook",
                "config": {"url": "https://example.com/rg-hook"},
            },
        )
        assert response.status_code == 201, response.text

    listed = client.get(
        f"/api/v1/workspaces/{workspace['id']}/escalation-rules", headers=headers
    ).json()
    assert [rule["name"] for rule in listed] == ["page-oncall", "page-manager"]

    duplicate = client.post(
        f"/api/v1/workspaces/{workspace['id']}/escalation-rules",
        headers=headers,
        json={
            "name": "page-oncall",
            "severity": "high",
            "minutes_to_escalate": 1,
            "kind": "webhook",
            "config": {"url": "https://example.com/rg-hook"},
        },
    )
    assert duplicate.status_code == 409

    invalid = client.post(
        f"/api/v1/workspaces/{workspace['id']}/escalation-rules",
        headers=headers,
        json={
            "name": "broken",
            "severity": "high",
            "minutes_to_escalate": 1,
            "kind": "webhook",
            "config": {},
        },
    )
    assert invalid.status_code == 422

    db = SessionLocal()
    try:
        incident_id = _make_incident(db, workspace, monitor, severity="high", minutes_old=11)
        _make_incident(db, workspace, monitor, severity="medium", minutes_old=60)
    finally:
        db.close()

    sent: list = []
    monkeypatch.setattr(
        incidents_module, "build_notifier", lambda kind, config: _RecordingNotifier(sent)
    )
    first = escalate_due_incidents()
    assert len(first["escalated"]) == 2
    assert len(sent) == 2

    second = escalate_due_incidents()
    assert second == {"escalated": [], "failed": []}
    assert len(sent) == 2

    resolved = client.patch(
        f"/api/v1/incidents/{incident_id}", headers=headers, json={"status": "resolved"}
    )
    assert resolved.status_code == 200
    assert escalate_due_incidents() == {"escalated": [], "failed": []}

    db = SessionLocal()
    try:
        types = [
            event.type
            for event in db.query(IncidentEvent)
            .filter(IncidentEvent.incident_id == incident_id)
            .all()
        ]
    finally:
        db.close()
    assert types.count("escalated") == 2
    assert "status:resolved" in types


def test_escalation_failure_is_recorded_and_retried(client, monkeypatch):
    headers, workspace, monitor = _setup_monitor(client)
    created = client.post(
        f"/api/v1/workspaces/{workspace['id']}/escalation-rules",
        headers=headers,
        json={
            "name": "retry-me",
            "severity": "high",
            "minutes_to_escalate": 0,
            "kind": "webhook",
            "config": {"url": "https://example.com/rg-hook"},
        },
    )
    assert created.status_code == 201

    db = SessionLocal()
    try:
        incident_id = _make_incident(db, workspace, monitor, severity="high", minutes_old=1)
    finally:
        db.close()

    monkeypatch.setattr(
        incidents_module, "build_notifier", lambda kind, config: _BrokenNotifier()
    )
    failed = escalate_due_incidents()
    assert len(failed["failed"]) == 1

    db = SessionLocal()
    try:
        failure_events = (
            db.query(IncidentEvent)
            .filter(
                IncidentEvent.incident_id == incident_id,
                IncidentEvent.type == "escalation_failed",
            )
            .count()
        )
    finally:
        db.close()
    assert failure_events == 1

    sent: list = []
    monkeypatch.setattr(
        incidents_module, "build_notifier", lambda kind, config: _RecordingNotifier(sent)
    )
    retried = escalate_due_incidents()
    assert len(retried["escalated"]) == 1
    assert len(sent) == 1
    assert "rg_escalations_total{status=\"failed\"}" in render_metrics()
