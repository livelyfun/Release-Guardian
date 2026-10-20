#!/usr/bin/env python3
"""Worker-restart resilience drill.

Validates that a run queued while the Celery worker is down survives the
outage and completes after the worker restarts.  Run it against a Docker
Compose stack (API + worker + Redis + Postgres) with ``WORKER_MODE=celery``.

Example:
    python scripts/resilience_drill.py --base-url http://localhost:8000

Exit codes: 0 = drill passed, 1 = drill failed, 2 = preflight failed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

TERMINAL = {"passed", "failed", "inconclusive"}


def compose(args, *command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-f", args.compose_file, *command],
        cwd=args.project_dir,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def setup(client: httpx.Client, args) -> dict:
    email = f"drill-{uuid.uuid4().hex[:10]}@example.com"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "drill-password-123", "name": "Drill"},
    )
    register.raise_for_status()
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    project = client.post(
        "/api/v1/projects", headers=headers, json={"workspace_id": workspace_id, "name": "Drill"}
    )
    project.raise_for_status()
    environment = client.post(
        f"/api/v1/projects/{project.json()['id']}/environments",
        headers=headers,
        json={"name": "drill", "base_url": args.target_url, "is_production": False},
    )
    environment.raise_for_status()
    monitor = client.post(
        f"/api/v1/environments/{environment.json()['id']}/monitors",
        headers=headers,
        json={
            "name": "Drill monitor",
            "kind": "http",
            "target_url": args.target_url,
            "interval_seconds": 300,
        },
    )
    monitor.raise_for_status()
    return {"headers": headers, "monitor_id": monitor.json()["id"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Worker restart resilience drill")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--target-url", default="https://example.com")
    parser.add_argument("--compose-file", default="docker-compose.yml")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default="/tmp/opencode/resilience-drill.json")
    args = parser.parse_args()

    report: dict = {
        "started_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "target_url": args.target_url,
        "steps": [],
    }

    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        health = client.get("/health")
        report["health"] = health.json() if health.status_code == 200 else health.text
        if health.status_code != 200 or health.json().get("worker_mode") != "celery":
            report["result"] = "preflight_failed"
            report["reason"] = "API unhealthy or WORKER_MODE is not 'celery'"
            print(json.dumps(report, indent=2))
            return 2

        context = setup(client, args)
        report["setup"] = "ok"

        stop = compose(args, "stop", "worker")
        report["steps"].append(
            {"step": "stop_worker", "returncode": stop.returncode, "stderr": stop.stderr[-500:]}
        )
        if stop.returncode != 0:
            report["result"] = "failed"
            print(json.dumps(report, indent=2))
            return 1

        try:
            created = client.post(
                f"/api/v1/monitors/{context['monitor_id']}/runs",
                headers=context["headers"],
                json={"trigger": "manual"},
            )
            report["steps"].append(
                {"step": "trigger_run", "status_code": created.status_code, "run": created.json()}
            )
            if created.status_code != 201:
                report["result"] = "failed"
                return 1
            run_id = created.json()["id"]

            time.sleep(2)
            queued = client.get(f"/api/v1/runs/{run_id}", headers=context["headers"]).json()
            report["steps"].append({"step": "confirm_queued", "run_status": queued["status"]})
            if queued["status"] not in {"pending", "running"}:
                report["result"] = "inconclusive"
                report["reason"] = "run completed while worker was stopped"
                return 1

            start = compose(args, "start", "worker")
            report["steps"].append(
                {"step": "start_worker", "returncode": start.returncode, "stderr": start.stderr[-500:]}
            )
            if start.returncode != 0:
                report["result"] = "failed"
                return 1

            started = time.perf_counter()
            while time.perf_counter() - started < args.timeout:
                detail = client.get(f"/api/v1/runs/{run_id}", headers=context["headers"]).json()
                if detail["status"] in TERMINAL:
                    report["recovery_seconds"] = round(time.perf_counter() - started, 2)
                    report["final_status"] = detail["status"]
                    report["steps"].append({"step": "recovered", "run": detail})
                    report["result"] = "passed" if detail["status"] == "passed" else "failed"
                    break
                time.sleep(2)
            else:
                report["result"] = "failed"
                report["reason"] = f"run did not complete within {args.timeout}s"
                return 1
        finally:
            # Always leave the stack running, even if the drill failed.
            compose(args, "start", "worker")

    print(json.dumps(report, indent=2))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report.get("result") == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
