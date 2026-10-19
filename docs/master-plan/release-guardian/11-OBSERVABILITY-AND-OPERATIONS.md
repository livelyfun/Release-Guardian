# 11 — OBSERVABILITY AND OPERATIONS

**Status:** Planning-only | **Date:** 2026-10-19

## Signal Coverage

| Area | Signals |
|---|---|
| Job execution | duration, success/failure, retries, per-type breakdown |
| Workers | availability, browser crashes, queue prefetch, lease/heartbeat gaps |
| Scheduler | missed schedules, fire delay, lease acquisition failures |
| Notifications | delays, webhook rejections, retry rates |
| Artifacts | storage write failures, orphaned/orphan-cleanup counts |
| Queue | backlog depth, age of oldest job, DLQ growth |
| Billing/usage | reconciliation failures, quota violations |
| AI (if enabled) | request cost, error rate, latency |
| Platform self-health | monitoring platform's own liveness (meta-monitoring) |

## Logging, Metrics, Traces

- Structured JSON logs with correlation IDs (workspace, project, run, job, trace).
- Metrics + traces via OpenTelemetry-compatible pipeline.
- Protected diagnostic evidence retained per retention policy.
- **Do not log customer secrets, auth tokens, or unnecessary personal data.**

## Alert Rules (Platform Self-Health)

- Missed scheduled checks beyond threshold.
- Sustained queue backlog / job age exceeding target.
- Scheduler lease not renewed.
- Worker pool unavailable / browser crash rate spike.
- Notification pipeline delay beyond objective.

## SLOs and Recovery Objectives

Proposed engineering targets requiring capacity/cost validation — **not guaranteed performance claims**:

| Objective | Target (proposed) |
|---|---|
| API availability | 99.9% |
| API latency | p95 / p99 documented |
| Scheduler max delay | bounded per tier |
| Failure-detection delay | bounded |
| Notification delivery | per-channel objective |
| Queue backlog threshold | alerting threshold |
| RTO / RPO | explicit per environment |

## Backup, Recovery, Resilience

- Database backups + **restore tests** (not just backup existence).
- Incident simulations, deployment recovery drills.
- Worker restart recovery and queue recovery validated.
- Cost-spike and storage-exhaustion response planned.

## Runbooks

Required runbooks (detection, containment, investigation, recovery, verification, escalation):

1. Website appears down
2. Worker pool unavailable
3. Queue backlog growing
4. Scheduler stopped
5. Database unavailable
6. Migration failed
7. Notification provider unavailable
8. False-positive incident storm
9. Suspected security breach
10. Credentials compromised
11. Storage exhausted
12. Cost spike
13. Deployment regression
14. Backup restoration
