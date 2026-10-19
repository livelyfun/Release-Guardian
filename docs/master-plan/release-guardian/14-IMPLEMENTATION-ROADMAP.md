# 14 — IMPLEMENTATION ROADMAP

**Project:** Release Guardian
**Date:** 2026-10-19
**Status:** Living document; updated as phases complete.

The roadmap covers every approved capability. Phase ordering is not permission to drop features.
Each phase lists its exit criteria; a phase is complete only when the criteria are verified.

## Phase Status

| Phase | Scope | Status |
|---|---|---|
| A — Discovery and decisions | Requirements, architecture, deployment, risk | Complete (docs 00–13) |
| B — Engineering foundation | Repo layout, tooling, local containers, CI, logging, tests | Complete |
| C — Identity and workspace model | Auth, workspaces, memberships, projects, environments, audit | Complete |
| D — Durable execution platform | Jobs, queue, scheduler, retries, execution tracking | Complete (retry/dead-letter hardening pending) |
| E — Monitoring and audit engine | HTTP checks, browser/Lighthouse execution, evidence | Partial (HTTP + asset retrieval; full Playwright pending) |
| F — Release verification | Deployment events, triggered suites, baselines, regression | Partial (events, triggered runs, latency baseline) |
| G — Incident management | Alert rules, lifecycle, notifications, escalation | Partial (lifecycle, webhook/email adapters) |
| H — Complete product experience | Dashboards, test builder, reports, API/CLI | Partial (read-oriented dashboard, REST API) |
| I — Advanced capabilities | AI assistance, analytics, billing, regions | Not started |
| J — Production readiness | Security validation, load/resilience, DR, runbooks | Not started |

## Milestones and Exit Criteria

### M1 — Engineering foundation (done)
- Repository flattened to `backend/`, `frontend/`, `docs/`.
- Ruff, pytest, TypeScript strict, ESLint, GitHub Actions.
- Docker Compose with Postgres, Redis, API, worker, scheduler.
- Exit criteria: `make lint`, `make test`, frontend build pass locally and in CI.

### M2 — Identity and tenancy (done)
- Register/login/refresh, JWT access and refresh tokens.
- Workspaces, memberships (owner/admin/developer/viewer), projects, environments.
- Audit log for sensitive mutations.
- Exit criteria: cross-tenant access tests return 404; role gates enforced server-side.

### M3 — Execution platform (done)
- Runs, step results, inline and Celery execution, manual trigger, scheduled due-check task.
- Exit criteria: run lifecycle persisted; duplicate scheduling prevented for active runs.

### M4 — Monitoring engine (in progress)
- HTTP availability, status/content assertions, redirect validation, SSRF guard.
- Remaining: full Playwright browser execution, Lighthouse audit integration, artifact storage.
- Exit criteria: browser journey runs in isolated worker with screenshots/traces retained.

### M5 — Release verification (in progress)
- Deployment ingestion, deployment-triggered runs, latency baseline and regression detection.
- Remaining: previous-known-good comparison, CI status checks, regression suppressions.
- Exit criteria: a deployment can be marked passed/failed/inconclusive from suite results.

### M6 — Incidents and notifications (in progress)
- Incident dedupe key, open/acknowledge/resolve, recurrence events, webhook delivery attempts.
- Remaining: escalation policies, maintenance windows, retry/backoff, more channels.
- Exit criteria: duplicate failures produce one incident and one notification per transition.

### M7 — Product experience and platform API (in progress)
- Next.js dashboard for workspaces, projects, monitors, runs, deployments, incidents, keys, audit.
- Remaining: test builder, exports, team management UI, API-key authentication for the public API.
- Exit criteria: a new user completes the core workflow without API calls.

### M8 — Production readiness (not started)
- Load/resilience tests, backup restore drill, security review, runbooks, cost validation.
- Exit criteria: documented SLOs met in staging; restore and rollback drills pass.

## Dependencies

- Browser execution depends on isolated worker images and network egress policy.
- Release verification depends on deployment webhook authentication.
- Billing depends on usage metering correctness and plan limits.
- AI assistance depends on redaction, evidence citation schema, and evaluation harness.

## Verification Gates

- Every change: backend lint + tests, frontend lint + typecheck + build.
- Schema change: Alembic migration with upgrade and downgrade verified.
- Security-sensitive change: SSRF and cross-tenant regression tests.
- Production exposure: threat model sign-off (doc 08) and secrets review.
