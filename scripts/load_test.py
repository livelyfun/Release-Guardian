#!/usr/bin/env python3
"""Reproducible load and backpressure test for the Release Guardian API.

The script creates a disposable user/workspace/project/environment and one
monitor per run request, then drives concurrent HTTP traffic.  It prints a JSON
summary and exits non-zero when the error rate exceeds ``--max-error-rate``.

Typical local run (API started with WORKER_MODE=inline, ALLOW_PRIVATE_URLS=true,
RATE_LIMIT_API_PER_MINUTE high enough for the chosen request count):

    python scripts/load_test.py --scenario all --requests 40 --concurrency 8 \
        --start-fixture --output /tmp/loadtest.json

The fixture target can also be started separately:
    python scripts/fixture_target.py --port 8099
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_target import serve  # noqa: E402

SETUP_TIMEOUT = 30.0


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * len(ordered))) - 1))
    return round(ordered[index], 2)


def summarize_latencies(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": round(max(values), 2),
        "mean": round(sum(values) / len(values), 2),
    }


async def setup(client: httpx.AsyncClient, args) -> dict:
    email = args.email or f"loadtest-{uuid.uuid4().hex[:10]}@example.com"
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "loadtest-password-123", "name": "Load Test"},
    )
    register.raise_for_status()
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    workspaces = (await client.get("/api/v1/workspaces", headers=headers)).json()
    workspace_id = workspaces[0]["id"]
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"workspace_id": workspace_id, "name": f"Load {uuid.uuid4().hex[:6]}"},
    )
    project.raise_for_status()
    environment = await client.post(
        f"/api/v1/projects/{project.json()['id']}/environments",
        headers=headers,
        json={
            "name": "load",
            "base_url": args.fixture_url,
            "is_production": False,
        },
    )
    environment.raise_for_status()

    monitors: list[str] = []
    if args.scenario in {"runs", "all"}:
        for index in range(args.requests):
            monitor = await client.post(
                f"/api/v1/environments/{environment.json()['id']}/monitors",
                headers=headers,
                json={
                    "name": f"Load monitor {index}",
                    "kind": "http",
                    "target_url": args.fixture_url,
                    "interval_seconds": 300,
                },
            )
            if monitor.status_code != 201:
                raise RuntimeError(f"monitor setup failed: {monitor.status_code} {monitor.text}")
            monitors.append(monitor.json()["id"])

    return {
        "email": email,
        "headers": headers,
        "workspace_id": workspace_id,
        "monitor_ids": monitors,
    }


async def timed(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> dict:
    started = time.perf_counter()
    try:
        response = await client.request(method, url, **kwargs)
        elapsed = (time.perf_counter() - started) * 1000
        try:
            body = response.json()
        except ValueError:
            body = None
        return {
            "status": response.status_code,
            "elapsed_ms": round(elapsed, 2),
            "body": body,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - connection errors are load-test evidence
        elapsed = (time.perf_counter() - started) * 1000
        return {
            "status": 0,
            "elapsed_ms": round(elapsed, 2),
            "body": None,
            "error": str(exc)[:300],
        }


def build_jobs(scenario: str, args, context: dict, client: httpx.AsyncClient) -> list:
    jobs = []
    if scenario == "read":
        for _ in range(args.requests):
            jobs.append(
                timed(
                    client,
                    "GET",
                    f"/api/v1/runs?workspace_id={context['workspace_id']}&limit=50",
                    headers=context["headers"],
                )
            )
    elif scenario == "runs":
        for monitor_id in context["monitor_ids"]:
            jobs.append(
                timed(
                    client,
                    "POST",
                    f"/api/v1/monitors/{monitor_id}/runs",
                    headers=context["headers"],
                    json={"trigger": "manual"},
                )
            )
    return jobs


async def execute(args) -> dict:
    fixture_server = None
    if args.start_fixture:
        fixture_server = serve(args.fixture_port)
        thread = threading.Thread(target=fixture_server.serve_forever, daemon=True)
        thread.start()
        args.fixture_url = f"http://127.0.0.1:{args.fixture_port}/"

    report: dict = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "scenario": args.scenario,
        "requests_per_scenario": args.requests,
        "concurrency": args.concurrency,
        "fixture_url": args.fixture_url,
    }

    limits = httpx.Limits(
        max_connections=max(10, args.concurrency * 2),
        max_keepalive_connections=max(10, args.concurrency),
    )
    async with httpx.AsyncClient(
        base_url=args.base_url,
        timeout=args.timeout,
        limits=limits,
    ) as client:
        health = await timed(client, "GET", "/health")
        report["api_health"] = health["body"]
        report["api_available"] = health["status"] == 200
        if not report["api_available"]:
            report["error"] = health["error"] or f"health status {health['status']}"
            return report

        setup_started = time.perf_counter()
        context = await setup(client, args)
        report["setup_seconds"] = round(time.perf_counter() - setup_started, 2)

        scenarios = ["read", "runs"] if args.scenario == "all" else [args.scenario]
        all_latencies: list[float] = []
        status_counts: dict[str, int] = {}
        run_status_counts: dict[str, int] = {}
        errors: list[str] = []
        measured = 0

        for scenario in scenarios:
            jobs = build_jobs(scenario, args, context, client)
            started = time.perf_counter()
            if args.concurrency > 1:
                semaphore = asyncio.Semaphore(args.concurrency)

                async def guarded(coro, semaphore=semaphore):
                    async with semaphore:
                        return await coro

                results = await asyncio.gather(*(guarded(job) for job in jobs))
            else:
                results = await asyncio.gather(*jobs)
            elapsed = time.perf_counter() - started

            scenario_latencies = [item["elapsed_ms"] for item in results]
            all_latencies.extend(scenario_latencies)
            measured += len(results)
            for item in results:
                key = str(item["status"])
                status_counts[key] = status_counts.get(key, 0) + 1
                if item["error"] and len(errors) < 5:
                    errors.append(item["error"])
                body = item["body"]
                if isinstance(body, dict) and body.get("status") in {
                    "pending",
                    "running",
                    "passed",
                    "failed",
                    "inconclusive",
                }:
                    run_key = body["status"]
                    run_status_counts[run_key] = run_status_counts.get(run_key, 0) + 1

            report[f"{scenario}_scenario"] = {
                "requests": len(results),
                "duration_seconds": round(elapsed, 3),
                "throughput_rps": round(len(results) / elapsed, 2) if elapsed else 0.0,
                "latency_ms": summarize_latencies(scenario_latencies),
            }

        failures = sum(count for status, count in status_counts.items() if status not in {"200", "201"})
        report["totals"] = {
            "requests": measured,
            "status_counts": status_counts,
            "run_status_counts": run_status_counts,
            "error_rate": round(failures / measured, 4) if measured else 0.0,
            "latency_ms": summarize_latencies(all_latencies),
        }
        report["errors"] = errors

    if fixture_server is not None:
        fixture_server.shutdown()
        fixture_server.server_close()

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Release Guardian load test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--scenario", choices=["read", "runs", "all"], default="all")
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--fixture-url", default="http://127.0.0.1:8099/")
    parser.add_argument("--fixture-port", type=int, default=8099)
    parser.add_argument("--start-fixture", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--email", default=None, help="Reuse an existing account (not recommended)")
    parser.add_argument("--output", default="loadtest-results.json")
    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=0.05,
        help="Fail when the share of non-2xx responses exceeds this value",
    )
    args = parser.parse_args()

    report = asyncio.run(execute(args))
    print(json.dumps(report, indent=2))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if not report.get("api_available"):
        return 2
    error_rate = report.get("totals", {}).get("error_rate", 1.0)
    return 0 if error_rate <= args.max_error_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
