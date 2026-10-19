# 02 — FEATURE CATALOG

**Status:** Planning-only | **Date:** 2026-10-19

| Module | Purpose | Priority (v1 scope) | Dependencies | Acceptance Criteria |
|---|---|---|---|---|
| AuthN/Z + RBAC | Users/workspaces/roles, sessions, audit | P0 | Auth provider, tenant scoping | Server-side authZ enforced; cross-tenant tests pass; audit entries written |
| Workspaces/Projects/Envs | Multi-tenant org model | P0 | RBAC | Tenant scoped queries; deletion semantics defined |
| HTTP/Endpoint Monitoring | Availability/latency/TLS/redirects/DNS/headers | P0 | Scheduler/workers | Timeouts, consecutive failures, maintenance windows |
| Real-Browser Synthetic | Playwright journeys, assertions, console/network, artifacts | P0 | Browser workers, isolation, artifacts | Step timeline, screenshots/traces, resource limits |
| Perf/SEO/a11y | Lighthouse (lab only) | P0 | Lighthouse, baselines | Thresholds, trends, distinguish from RUM |
| Deployment Verification | Webhooks/deploy events, post-deploy checks, correlation | P0 | GitHub integration, events | Deploy→verify→incident correlation |
| Baselines/Regression | Healthy baselines, thresholds (fixed/statistical), flakiness | P0 | History, comparison | N-samples rule, noise handling, reset rules |
| Incidents | Lifecycle, severity, dedup, grouping, ack/resolve, timeline | P0 | Alerts, notifications | Dedup prevents storms; evidence linked |
| Notifications | Provider-agnostic, retries, dedup | P0 | Channels, secrets | Backoff+jitter, retry caps, validation |
| Reporting/Dashboards | Health, trends, step details, exports, audit | P1 | Aggregations, authZ | Accessible, PII redaction |
| API/CLI/DevEx | REST (OpenAPI), scoped keys, signed webhooks, idempotency | P1 | AuthZ, rate limits | Versioned, standard errors, pagination |
| AI Diagnosis (optional) | Evidence-cited advisory | P2 (defer) | Provider, evals, guardrails | Never overrides deterministic result; uncertainty marked |
| Billing/Quotas (optional) | Plans/usage/meters/limits | P2 (defer) | Metering events | Isolated from core; track usage now |

Notes: Sequencing manages complexity (not dropping features). Full scope preserved.
