# 04 — SYSTEM ARCHITECTURE

**Status:** Planning-only | **Date:** 2026-10-19

## System Context (Logical)

```text
Users (Web)
  -> Vercel (Next.js) [Auth, Dashboards, Reports]
       -> FastAPI Control Plane (REST, OpenAPI) [AuthZ, RBAC, Quotas]
            ├─ PostgreSQL (tenants, projects, checks, runs, steps, incidents, baselines, audits)
            ├─ Redis (broker, locks, dedup, rate limits)
            ├─ S3-compatible (artifacts: screenshots/traces/HAR/Lighthouse; signed URLs)
            └─ Celery/RQ Workers (isolated browser containers)
                 ├─ Playwright (Chromium)
                 ├─ Lighthouse (lab)
                 └─ HTTP checks

External: GitHub webhooks/deploys, Notifications (Email/Webhook/Slack/Teams), Outbound to monitored sites (SSRF-controlled)
```

## Component Boundaries

- **Control Plane (stateless):** Request serving, validation, authZ, job creation, scheduling coordination. Tenant-scoped by default.
- **Scheduler:** Celery Beat or cron with advisory locks; dedup, maintenance windows, missed schedules.
- **Workers (heavy):** Separate from API; browser execution isolated (resource limits, ephemeral FS, no host net where unsafe). One job per process/container lifetime where practical.
- **Data plane:** PG (durable), Redis (ephemeral/coordination), Object Storage (artifacts, immutable, lifecycle).

## Deployment Topology (Recommended)

| Component | Hosting (proposed) | Notes |
|---|---|---|
| Frontend (Next.js) | Vercel | Preview per PR, edge, TLS |
| API + Scheduler | Managed containers (Render/Railway/Fly.io) | Stateless API, health/readiness, rolling deploys |
| Browser Workers | Isolated worker pool (separate containers) | Horizontally scaled by queue depth; CPU/mem/time caps per job |
| PostgreSQL | Neon (managed) | PITR, backups, branching (preview); connection pooling strategy TBD |
| Redis | Managed (Upstash/Redis Cloud) | Broker + locks + rate limits; validate semantics |
| Object Storage | R2 (S3-compatible) | Signed URLs (tenant/project scoped, short expiry), lifecycle retention |

## Sequences (High-Level)

**Job Execution:** Schedule due → API enqueues versioned job → Worker leases (visibility timeout) → Executes with timeouts → Writes results/artifacts → Updates PG → Emits events → Releases lease/completes.

**Deployment Verification:** GitHub deploy webhook (signed, validated) → Create deploy event → Enqueue post-deploy checks (critical journeys) → Run → Correlate to release → Open/update incident if failed.

**Evidence Flow:** Artifacts written to storage → DB stores references only → Access via short-lived signed URLs (authZ checked).
