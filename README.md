# Release Guardian

[![CI](https://github.com/livelyfun/Release-Guardian/actions/workflows/ci.yml/badge.svg)](https://github.com/livelyfun/Release-Guardian/actions/workflows/ci.yml)

Multi-tenant website reliability, synthetic monitoring, and release verification.

Release Guardian runs deterministic HTTP, real-browser, and Lighthouse checks
against your sites, stores the evidence, detects regressions, correlates failures
with deployments, and manages incidents through to resolution. The deterministic
engine is the source of truth; AI assistance is a planned advisory layer only.

> **Status: early development (pre-1.0).** The engineering foundation and the
> first vertical slice are implemented and tested locally. There is no hosted
> service, no published release, and no external security audit. Interfaces and
> the database schema will change. See [Limitations](#limitations) before
> deploying this anywhere that matters.

## What works today

- **Identity and tenancy** — email/password auth with scrypt, JWT access and
  refresh tokens, workspaces, roles (owner/admin/developer/viewer), invitations,
  API keys with scopes, audit log.
- **Projects and environments** — group monitors by site and environment
  (production, staging, preview).
- **Monitors and runs** — HTTP checks with status/latency assertions, Playwright
  browser journeys with per-step results, screenshots and optional HAR/trace, and
  Lighthouse performance checks with thresholds.
- **Scheduling and dispatch** — Celery beat dispatches due monitors under a Redis
  lock; browser and Lighthouse work runs on a dedicated queue and worker.
- **Deployments** — release events trigger runs and derive a deployment status.
- **Baselines and regressions** — latency baselines, regression detection,
  previous-known-good comparison, and time-boxed regression suppressions.
- **Incidents** — deduplicated incidents with a timeline, consecutive-failure
  thresholds, maintenance windows, escalation ladders, signed webhooks, SMTP
  email, and retry with backoff.
- **Operations** — health/readiness/metrics endpoints, structured JSON logs with
  request IDs, Prometheus alerts, Grafana dashboard, runbooks, backup/restore and
  rollback drills, SLO definitions, and a cost model.

## Architecture

```
                    ┌──────────────────┐
   browser ────────▶│  Next.js         │  dashboard (App Router)
                    └────────┬─────────┘
                             │ REST /api/v1
                    ┌────────▼─────────┐        ┌──────────────┐
                    │  FastAPI         │───────▶│  PostgreSQL  │
                    │  control plane   │        └──────────────┘
                    └───┬──────────┬───┘
                        │          │
              ┌─────────▼──┐   ┌───▼──────────┐
              │  Redis     │   │  S3-compatible│
              │  broker,   │   │  artifacts    │
              │  locks     │   │  (optional)   │
              └─────┬──────┘   └──────────────┘
                    │
        ┌───────────┴────────────┬──────────────────┐
        │                        │                  │
┌───────▼────────┐   ┌───────────▼────────┐  ┌──────▼─────────┐
│ worker         │   │ browser worker     │  │ scheduler      │
│ queue:         │   │ queues: browser,   │  │ celery beat    │
│ release_guardian│  │ lighthouse         │  │                │
└────────────────┘   └────────────────────┘  └────────────────┘
```

| Path | Contents |
|---|---|
| `backend/app/api/v1` | FastAPI routers, dependencies, tenant access checks |
| `backend/app/services` | Checks, browser, storage, SSRF guard, notifications |
| `backend/app/workers` | Celery app, task modules, dispatch and locking |
| `backend/alembic` | Migrations (linear chain) |
| `frontend/src` | Next.js dashboard, `@/*` → `frontend/src/*` |
| `docs/master-plan` | Product, architecture, security, roadmap |
| `docs/operations` | SLOs, runbooks, deployment, backup, cost |

## Quick start

### Docker Compose (API, workers, Postgres, Redis)

```bash
cp .env.example .env      # edit JWT_SECRET, WEBHOOK_SIGNING_SECRET, CORS_ORIGINS
docker compose up -d --build
```

The `api` container applies migrations on boot. Uvicorn listens on
`http://localhost:8000` (docs at `/docs`). The dashboard is not part of the
Compose stack; run it separately:

```bash
cd frontend && npm ci && NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run dev
# http://localhost:3000
```

### Local development

```bash
cp .env.example .env
make install      # backend + frontend dependencies
make up           # Postgres and Redis
make migrate
make dev-api      # :8000
make dev-worker   # Celery worker, separate shell
make dev-web      # :3000
```

### Checks

```bash
make lint     # ruff + ESLint/tsc
make test     # backend pytest
make check    # lint + tests + frontend build
```

## Configuration

Every variable is documented in [`.env.example`](.env.example). The important
ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL (`postgresql+psycopg://…`). SQLite is development only. |
| `REDIS_URL` | Celery broker, rate limits, scheduler and run locks |
| `JWT_SECRET` | Must be ≥32 random characters in production |
| `WEBHOOK_SIGNING_SECRET` | Signs outbound webhooks (≥16 characters) |
| `CORS_ORIGINS` | Exact dashboard origin; wildcards are rejected in production |
| `WORKER_MODE` | `celery` (default) or `inline` for single-process development |
| `S3_*` | Optional artifact storage; without it, artifact links are empty |
| `SMTP_*` | Optional email notifications |
| `NEXT_PUBLIC_API_URL` | Dashboard → API base URL, baked in at build time |

`ENVIRONMENT=production` enables a startup guard that refuses to boot with a
default JWT secret, a short webhook secret, SQLite, `ALLOW_PRIVATE_URLS=true`,
or a wildcard CORS origin.

## Limitations

Read this before treating the project as production-ready.

- **Pre-1.0.** Schema and API may change without migration paths between
  releases. Pin a commit if you deploy it.
- **No hosted service.** This repository is the whole product; there is no
  managed offering.
- **Email notifications need SMTP.** The SMTP transport is implemented, but if
  `SMTP_HOST` is unset, email channels fail with a configuration error rather
  than falling back to another transport.
- **Artifacts are optional.** Without S3-compatible storage, runs still execute
  and record upload failures as evidence; screenshot and report links are empty.
- **Browser and Lighthouse checks need their dependencies.** Playwright browsers
  and the Lighthouse CLI live in `Dockerfile.worker`. The API image cannot run
  them.
- **AI is structural only.** `AIConfiguration` exists; there is no AI execution
  or evaluation harness yet.
- **Billing, plans, and multi-region are not implemented.**
- **No external penetration test.** Controls are covered by tests and a written
  review, but the go-live gate in
  [`docs/operations/PRODUCTION-CHECKLIST.md`](docs/operations/PRODUCTION-CHECKLIST.md)
  is not signed off.
- **SSRF defense is application-layer.** See below — network isolation is a
  deployment requirement, not a nice-to-have.

## Self-hosting security requirements

Release Guardian fetches URLs supplied by its users, which is an SSRF surface by
design. The application validates scheme, host, and resolved address, re-checks
every redirect hop, and intercepts browser subrequests — but application checks
cannot fully stop DNS rebinding between validation and connection.

If you expose it to untrusted users you **must** run the workers in a network
that cannot reach cloud metadata endpoints or your internal network, and apply an
egress firewall that permits only public HTTP/HTTPS. Keep `ALLOW_PRIVATE_URLS`
unset. Details:
[docs/operations/PRODUCTION-DEPLOYMENT.md](docs/operations/PRODUCTION-DEPLOYMENT.md#network-isolation-and-ssrf-self-host-requirement).

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md).

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). For anything larger than a bug fix,
open an issue first.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).

Copyright (C) 2026 livelyfun.

AGPL means you may self-host, modify, and redistribute this software, but if you
run a modified version as a network service, you must offer its source to users.
If that does not fit your use case, contact the maintainers about alternative
terms.
