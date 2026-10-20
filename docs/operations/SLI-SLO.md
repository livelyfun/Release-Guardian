# SLIs, SLOs, and Recovery Objectives

**Status:** Provisional engineering targets. M8 requires these to be validated
against staging evidence before they become commitments.
**Last updated:** 2026-10-20

## Scope

This document defines what "healthy" means for the control plane and workers,
how each objective is measured from `/metrics`, and what to do when an error
budget is exhausted. Targets are deliberately conservative; they are not
marketing performance claims.

## Indicators and objectives

| # | SLO | SLI definition | Target | Window |
|---|---|---|---|---|
| 1 | API availability | Non-5xx responses / all API responses | 99.9% | 30 days |
| 2 | API read latency | p95 of `GET` API requests | ≤ 500 ms | 30 days |
| 3 | API write latency | p95 of non-`GET` API requests (enqueue time) | ≤ 1 000 ms | 30 days |
| 4 | Run completion integrity | Terminal runs that are not `inconclusive` / all terminal runs | ≥ 99.5% | 30 days |
| 5 | Scheduler freshness | Minutes where `time() - rg_scheduler_last_success_timestamp_seconds < 180` | 99.9% | 30 days |
| 6 | Queue age | p95 age of the oldest pending run | ≤ 300 s | 7 days |
| 7 | Notification delivery | Successful channel attempts / all attempts | ≥ 99% | 7 days |
| 8 | Artifact uploads | Successful uploads / all upload attempts | ≥ 99.5% | 7 days |

Run *outcomes* (`passed`/`failed`) are not availability SLOs: a failing target is
a valid product result, not a platform failure. SLO 4 tracks whether the
platform could produce a trustworthy verdict.

### Error budget

For SLO 1 at 99.9% over 30 days, the budget is **43 min 12 s** of full API
unavailability. Budget policy:

- **< 50% consumed:** normal change velocity.
- **50–80%:** review recent changes and alert noise; no risky migrations.
- **> 80%:** freeze non-essential deploys until the burn rate returns to normal.
- **100%:** incident review required; reliability work precedes features.

## Measurement queries

Metrics are exposed at `GET /metrics` (protect with `METRICS_TOKEN`). Prometheus
must scrape every API replica; counters are process-local and aggregated in
queries.

### SLO 1 — API availability

```promql
1 - (
  sum(rate(rg_api_requests_total{status=~"5.."}[5m]))
  /
  sum(rate(rg_api_requests_total[5m]))
)
```

### SLO 2/3 — API latency

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(rg_api_request_duration_seconds_bucket{method="GET"}[5m]))
)
```

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(rg_api_request_duration_seconds_bucket{method!="GET"}[5m]))
)
```

### SLO 4 — Run completion integrity

```promql
sum(rate(rg_runs_total{status!="inconclusive"}[30m]))
/
sum(rate(rg_runs_total[30m]))
```

### SLO 5 — Scheduler freshness

```promql
time() - max(rg_scheduler_last_success_timestamp_seconds)
```

### SLO 6 — Queue age and depth

```promql
max(rg_oldest_pending_run_age_seconds)
max(rg_queue_depth)
max(rg_pending_runs)
```

### SLO 7 — Notification delivery

```promql
sum(rate(rg_notification_attempts_total{status="sent"}[30m]))
/
sum(rate(rg_notification_attempts_total[30m]))
```

### SLO 8 — Artifact uploads

```promql
sum(rate(rg_artifact_uploads_total{status="success"}[30m]))
/
sum(rate(rg_artifact_uploads_total[30m]))
```

### Supporting signals

| Signal | Query |
|---|---|
| Sweeper freshness | `time() - rg_sweeper_last_success_timestamp_seconds` |
| Stale runs recovered | `sum(rate(rg_stale_runs_total{action="redispatched"}[15m]))` |
| Stale runs timed out | `sum(rate(rg_stale_runs_total{action="timed_out"}[15m]))` |
| Active executions | `sum(rg_active_runs)` |
| SSRF rejections | `sum(rate(rg_blocked_urls_total[15m])) by (reason)` |
| Escalation failures | `sum(rate(rg_escalations_total{status="failed"}[15m]))` |

## Alert rules (starting points)

Machine-readable rules live in [`prometheus-alerts.yml`](prometheus-alerts.yml).
Import [`grafana-dashboard.json`](grafana-dashboard.json) for the matching
platform overview dashboard. Both are starting points: tune thresholds against
the staging baseline before production.

| Alert | Expression | For | Severity |
|---|---|---|---|
| ApiDown | `up{job="release-guardian-api"} == 0` | 2m | critical |
| ApiHighErrorRate | availability < 99% over 15m | 10m | critical |
| ApiLatencyHigh | read p95 > 1s over 15m | 10m | warning |
| SchedulerStale | `time() - rg_scheduler_last_success_timestamp_seconds > 300` | 5m | critical |
| SweeperStale | `time() - rg_sweeper_last_success_timestamp_seconds > 300` | 5m | warning |
| QueueBacklog | `rg_pending_runs > 50` or oldest pending > 300s | 10m | warning |
| StuckRunGrowth | `rate(rg_stale_runs_total{action="timed_out"}[1h]) > 0.1` | 15m | warning |
| NotificationFailures | failure ratio > 5% over 30m | 15m | warning |
| EscalationFailures | `rate(rg_escalations_total{status="failed"}[15m]) > 0` | 15m | warning |
| ArtifactFailures | failure ratio > 1% over 30m | 15m | warning |
| ReadinessFailing | `/ready` returns 503 | 5m | critical |
| SsrfSpike | `sum(rate(rg_blocked_urls_total[5m])) > 5` | 10m | warning |

`/health` is liveness (process up). `/ready` is readiness (database reachable,
plus Redis when `WORKER_MODE=celery`). Route `/ready` to load balancers; do not
route traffic to a replica that fails it.

## Recovery objectives

| Asset | RPO | RTO | Mechanism |
|---|---|---|---|
| Postgres (metadata, runs, incidents) | ≤ 15 min | ≤ 60 min | Managed PITR or daily dump + WAL; drill in [BACKUP-RESTORE.md](BACKUP-RESTORE.md) |
| Redis queue | Best effort | ≤ 15 min | AOF enabled; pending runs are re-dispatched by the sweeper |
| Object storage (artifacts) | ≤ 24 h | ≤ 4 h | Provider versioning/lifecycle; artifacts are regenerable from runs |
| Deployment rollback | n/a | ≤ 15 min | Previous image tag + expand/contract migrations |

**Redis is not the system of record.** The `runs` table is. A total Redis loss
can delay execution but the sweeper re-dispatches pending runs after
`PENDING_RUN_TIMEOUT_SECONDS`.

## Known measurement gaps

Documented honestly so they are not mistaken for coverage:

1. **Traces** are not exported. Structured JSON logs carry `request_id`; an
   OpenTelemetry exporter is still a follow-up (doc 11 target).
2. **Per-tenant queue metrics** are not labelled (intentional: cardinality).
3. **Scheduler enqueue delay** is measured by tick freshness, not per-monitor
   lateness. `last_checked_at` in the database is the source for per-monitor
   delay analysis.
4. **Notification provider latency** is not measured separately from attempt
   success.
5. **Histogram buckets** are fixed; changing them requires a code change and
   dashboard update.
