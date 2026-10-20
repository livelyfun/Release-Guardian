# Load and Resilience Testing

**Status:** tooling complete; local baseline recorded; staging run outstanding.
**Last updated:** 2026-10-20

## What exists

| Tool | Purpose |
|---|---|
| `scripts/fixture_target.py` | Local HTTP target with `/`, `/health`, `/slow`, `/fail` |
| `scripts/load_test.py` | Concurrent read/run load with latency percentiles and JSON report |
| `scripts/resilience_drill.py` | Stops the worker, queues a run, restarts, measures recovery |
| `backend/tests/test_production_readiness.py` | Unit/integration coverage for sweeper, locks, readiness, metrics, SSRF, storage outage |

Both scripts write JSON evidence so results can be attached to a release or
incident without copy/paste.

## Load scenarios

| Scenario | Traffic | What it measures |
|---|---|---|
| `read` | `GET /api/v1/runs?workspace_id=…` | API + database read path |
| `runs` | `POST /api/v1/monitors/{id}/runs` across distinct monitors | Admission control + execution path |
| `all` | `read` then `runs` | Both, reported separately |

The `runs` scenario creates one monitor per request so duplicate-active-run
rejection (409) is not counted as an error. With `WORKER_MODE=inline` each run
finishes before the response; with Celery the response measures enqueue latency
only and completion must be checked separately.

### Local run

Prerequisites: API on `:8010` with an isolated SQLite file, inline workers,
private URLs allowed (the fixture is loopback), and high rate limits.

```bash
# terminal 1
cd backend
DATABASE_URL=sqlite:////tmp/opencode/rg-loadtest.db \
WORKER_MODE=inline ALLOW_PRIVATE_URLS=true \
JWT_SECRET=loadtest-secret-0123456789abcdef0123456789 \
RATE_LIMIT_API_PER_MINUTE=100000 RATE_LIMIT_AUTH_PER_MINUTE=1000 \
.venv/bin/uvicorn app.main:app --port 8010

# terminal 2
python scripts/load_test.py --base-url http://127.0.0.1:8010 \
  --scenario all --requests 40 --concurrency 8 --start-fixture \
  --output /tmp/opencode/loadtest.json
```

### Local baseline (2026-10-20)

This is a **single-process SQLite baseline**, not a capacity claim for staging
or production. It exists to prove the harness works and to catch gross
regressions.

| Metric | Read scenario | Run scenario |
|---|---|---|
| Requests | 40 | 40 |
| Concurrency | 8 | 8 |
| Throughput | 81.1 req/s | 20.4 runs/s |
| p50 latency | 74.1 ms | 286.9 ms |
| p95 latency | 160.7 ms | 686.7 ms |
| p99 latency | 184.8 ms | 1 477.3 ms |
| Errors | 0 | 0 |
| Run outcomes | n/a | 40 passed |

Interpretation: HTTP checks against a local fixture cost roughly 49 ms of
execution each up to p50; the write path is dominated by check execution +
incident/baseline bookkeeping, not by HTTP overhead.

Raw report: [`evidence/loadtest-local-2026-10-20.json`](evidence/loadtest-local-2026-10-20.json).

### Staging gate

Run against staging (Postgres + Redis + Celery + at least 2 workers) at the
capacity planned for launch:

```bash
python scripts/load_test.py --base-url https://staging.example.com \
  --scenario all --requests 200 --concurrency 20 \
  --fixture-url https://fixture.staging.example.com/ \
  --output docs/operations/evidence/loadtest-staging-$(date +%F).json
```

Required before M8 sign-off:

- [ ] Error rate ≤ 1% (excluding intentional 409/429 admission responses).
- [ ] Read p95 ≤ 500 ms, write/enqueue p95 ≤ 1 000 ms.
- [ ] 429 rate is explainable by configured limits; no unexpected 5xx.
- [ ] `rg_queue_depth` returns to baseline within 5 minutes.
- [ ] Oldest pending run stays under 300 s during the run.
- [ ] All triggered runs reach a terminal state; sweeper timeout count is 0.
- [ ] API CPU/memory and database connections stay within provider limits.

Save the JSON report and the Prometheus range screenshots as evidence.

## Resilience matrix

| Failure | Mechanism | Verified by | Residual risk |
|---|---|---|---|
| Worker dies mid-run | `acks_late`, per-run Redis lock, sweeper marks over-time runs `inconclusive` | `test_sweeper_times_out_stuck_running_run`, `resilience_drill.py` | Lock fails open if Redis is down |
| Worker down before task starts | Queue persists; sweeper re-dispatches pending runs | `resilience_drill.py` | Tasks lost if Redis loses AOF data |
| Broker redelivery | Per-run lock + terminal-status guard | `test_execute_run_ignores_duplicate_lock`, `test_execute_run_skips_terminal_run` | Duplicate dispatch is ignored, not journalled |
| Queue backlog | Per-monitor/workspace admission control, queue metrics, alerts | `test_manual_trigger_rejects_duplicate_active_run`, `test_manual_trigger_enforces_workspace_capacity` | No per-tenant fair scheduling yet |
| Multiple schedulers | Redis scheduler lock + active-run check | `test_scheduler_skips_when_lock_held` | Lock TTL is 55 s; a slow tick can overlap |
| Redis outage | In-memory rate limiting fallback; scheduler lock fails open; `/ready` reports Redis error | `test_rate_limit_backend_selection`, readiness check | Duplicate execution possible during outage |
| Storage outage | Upload errors are caught; run records `screenshot_error`/`report_error` and continues | `test_storage_outage_raises_controlled_error` | Artifact is lost; no retry queue |
| Browser crash | Browser exception becomes a failed step with evidence | Browser unit tests, runbooks | Container-level isolation is deployment config |
| SSRF attempt | URL validation + browser route guard + Lighthouse validation | `test_url_guard_blocks_metadata_address` | DNS rebinding needs egress firewall |
| Database failover | Managed failover; `/ready` gates traffic | Runbook 5 | Not exercised in local env |

### Worker restart drill

Against a Compose stack with `WORKER_MODE=celery`:

```bash
python scripts/resilience_drill.py --base-url http://localhost:8000 \
  --compose-file docker-compose.yml --target-url https://example.com \
  --output docs/operations/evidence/resilience-$(date +%F).json
```

Pass criteria: the run is `pending` while the worker is stopped, completes
within `--timeout` after restart, and `recovery_seconds` is recorded. The script
always restarts the worker, even on failure.

## Not implemented

- A true dead-letter queue. Exhausted or lost tasks are recovered by the
  sweeper (re-dispatch or timeout), not quarantined for inspection.
- Automated database failover or chaos testing of the managed provider.
- Per-tenant fair queueing.
- Distributed tracing. Structured logs + request IDs are available.
