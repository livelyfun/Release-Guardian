# 15 — RISK REGISTER

**Project:** Release Guardian
**Date:** 2026-10-19
**Method:** Engineering judgment from the current implementation and docs 00–13. Not a substitute
for a formal security review before production exposure.

## Ranked Risks

| ID | Risk | Likelihood | Impact | Mitigation | Verification |
|---|---|---|---|---|---|
| R1 | SSRF via user-supplied target URLs reaches internal services or cloud metadata | Medium | Critical | `url_guard.py` scheme/host/IP validation, redirect re-validation per hop, private ranges blocked, `ALLOW_PRIVATE_URLS` only for local dev; network egress policy required | Unit tests for loopback/private/link-local/redirect; egress firewall test in staging |
| R2 | Cross-tenant data access through missing membership checks | Medium | Critical | Server-side membership on every scoped query (`deps.py`, `access.py`); client IDs never trusted | Cross-tenant pytest cases for projects/runs/incidents/keys |
| R3 | Browser worker compromise through malicious page content | Medium | High | Disposable worker containers, unprivileged user, resource limits, profile cleanup, egress restriction | Container hardening checklist; incident drill |
| R4 | Duplicate or lost jobs under at-least-once delivery | High | Medium | Idempotent run creation, active-run dedupe in scheduler, terminal statuses, bounded retries | Scheduler dedupe test; queue redelivery drill |
| R5 | Scheduler silently stops, missing checks unnoticed | Medium | High | Celery beat plus platform alert on heartbeat/scheduler lateness; monitor queue age | Operational alert; synthetic self-check |
| R6 | Secret leakage in logs, errors, or artifacts | Medium | High | Redaction policy, no secret logging, encrypted credential storage, scoped API keys | Log review; secret scanner in CI (pending) |
| R7 | Flaky browser checks create false incidents | High | Medium | Consecutive-failure policy, retry only where safe, baseline samples, evidence retention | Flake-rate report before enabling alerts |
| R8 | Cost overrun from uncontrolled browser execution | Medium | Medium | Per-workspace quotas, timeouts, concurrency limits, usage records | Usage dashboard and quota tests |
| R9 | Migration failure or destructive schema change | Low | High | Versioned Alembic migrations, backward-compatible rollout, backup and restore drill | Upgrade/downgrade verified per migration; restore drill |
| R10 | Notification storm from repeated failures | Medium | Medium | Incident dedupe key, one notification per transition, suppression windows (pending) | Dedupe test; suppression test |
| R11 | AI prompt injection via untrusted page content (when AI enabled) | Medium | High | AI is advisory; untrusted input never grants tools; redaction; evidence citation; evaluation set | Evaluation harness before enabling AI |
| R12 | Vendor lock-in / provider limits (queue, database, workers) | Medium | Medium | Provider-neutral interfaces, portable SQL, documented exit path | Portability review each phase |

## Residual Risk Notes

- R1 remains high until network egress controls exist; application validation alone is insufficient.
- R4 is inherent to queue-based delivery; correctness depends on idempotent writes, which are
  implemented for run creation but not yet for all future job types.
- R7 cannot be eliminated; it must be measured and tuned per monitor.

## Open Verification Items

- Automated dependency and container scanning is not yet wired into CI.
- No load, soak, or chaos test has been executed.
- No external penetration test or formal threat-model review has been performed.
