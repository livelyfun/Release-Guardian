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
| D — Durable execution platform | Jobs, queue, scheduler, retries, execution tracking | Complete (retries via sweeper; no quarantined DLQ) |
| E — Monitoring and audit engine | HTTP checks, browser/Lighthouse execution, evidence | Partial (HTTP, Playwright, Lighthouse, screenshots/traces/HAR; artifact redaction pending) |
| F — Release verification | Deployment events, triggered suites, baselines, regression | Partial (events, triggered runs, baselines; CI status checks/suppressions pending) |
| G — Incident management | Alert rules, lifecycle, notifications, escalation | Partial (lifecycle, retries, escalation, maintenance windows; real email transport pending) |
| H — Complete product experience | Dashboards, test builder, reports, API/CLI | Partial (dashboard incl. usage/artifacts/admin UI, REST API, API keys; test builder/exports/team UI/CLI pending) |
| I — Advanced capabilities | AI assistance, analytics, billing, regions | Structural only (`AIConfiguration`; features not built) |
| J — Production readiness | Security validation, load/resilience, DR, runbooks | In progress (deliverables built; staging SLO + drill sign-off pending) |

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

### M4 — Monitoring engine (partial)
- HTTP availability, status/content assertions, redirect validation, SSRF guard.
- Playwright browser journeys with route-level SSRF checks, console/network
  evidence, a final screenshot, optional Playwright trace/HAR capture, and
  optional per-step screenshots.
- Lighthouse audits with category scores, thresholds, and an optional JSON
  report artifact.
- Remaining: artifact redaction and staging validation of trace/HAR capture.
- Exit criteria: a browser journey runs in the worker and retains a screenshot;
  Lighthouse retains scores/report. Met locally; staging evidence pending.

### M5 — Release verification (partial)
- Deployment ingestion, deployment-triggered runs, latency baseline and
  regression detection, deployment status derivation.
- Remaining: previous-known-good comparison, CI status checks, regression
  suppressions.
- Exit criteria: a deployment can be marked passed/failed/inconclusive from
  suite results. Met.

### M6 — Incidents and notifications (partial)
- Incident dedupe key, open/acknowledge/resolve, recurrence events, webhook
  delivery attempts, HMAC-signed outgoing webhooks, exponential backoff with
  jitter and a retry cap for failed deliveries.
- Escalation ladder: rules per workspace/severity, ordered by elapsed minutes,
  fired at most once per incident, retried on delivery failure, CRUD API, and a
  scheduler sweep.
- Maintenance windows (workspace/project/environment/monitor scoped) suppress
  incident creation; consecutive-failure thresholds prevent single-blip pages.
- Remaining: real email transport, more channels.
- Exit criteria: duplicate failures produce one incident and one notification
  per transition. Met for webhooks.

### M7 — Product experience and platform API (partial)
- Next.js dashboard for workspaces, projects, monitors, runs, deployments,
  incidents, keys, audit, usage totals, artifact previews, escalation rules,
  and maintenance windows.
- API-key authentication and workspace role gates.
- Remaining: visual test builder, exports, team management UI, CLI.
- Exit criteria: a new user completes the core workflow without API calls.
  Met for the read/trigger workflow; authoring a browser journey still needs
  JSON config.

### M8 — Production readiness (in progress)
- Structured JSON logs with request IDs; `/health`, `/ready`, `/metrics`
  (optional bearer token).
- SLOs, alert rules, error budgets, 14 runbooks.
- Load test, fixture target, worker-restart drill, backup/restore drill,
  rollback procedure.
- Admission control, Redis rate limiting, scheduler/run locks, stale-run
  sweeper, Celery time limits, Redis AOF, container hardening, configurable
  Postgres pool sizing, separate browser/Lighthouse worker queues, and an
  artifact-retention pruning task.
- Security self-review with residual-risk register and go-live checklist.
- Cost model and validation checklist.
- Remaining: run load/restore/rollback drills in staging and record evidence;
  external penetration test; egress firewall verification.
- Exit criteria: documented SLOs met in staging; restore and rollback drills
  pass. **Not yet met — see `docs/operations/PRODUCTION-CHECKLIST.md`.**

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
