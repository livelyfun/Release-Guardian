# Release Guardian

Multi-tenant website reliability, synthetic monitoring, and release-verification platform.

Release Guardian runs deterministic HTTP and real-browser checks against your websites, stores
evidence, detects regressions, correlates failures with deployments, and manages incidents.
AI-assisted diagnosis is an optional, advisory layer only; the deterministic engine remains the
source of truth.

## Repository layout

```
backend/            FastAPI control plane, SQLAlchemy models, Celery workers
frontend/           Next.js (App Router) dashboard
docs/master-plan/   Product, architecture, security, and operations plans
.github/workflows/  CI pipeline
docker-compose.yml  Local Postgres, Redis, API, and worker
```

## Quick start (local)

```bash
cp .env.example .env
make install          # install backend + frontend dependencies
make up               # start Postgres and Redis
make migrate          # apply database migrations
make dev-api          # run the API on http://localhost:8000
make dev-worker       # run the Celery worker (separate shell)
make dev-web          # run the dashboard on http://localhost:3000
```

API documentation is available at `http://localhost:8000/docs`.

## Tests and quality

```bash
make test             # backend pytest suite
make lint             # ruff (backend) + eslint/tsc (frontend)
make check            # full local gate: lint + tests + frontend build
```

## Core concepts

| Concept | Meaning |
|---|---|
| Workspace | Tenant boundary; owns projects, members, API keys, and incidents |
| Project | A website or application being monitored |
| Environment | Production, staging, preview, or custom target URL for a project |
| Monitor | A scheduled HTTP, browser, or performance check against an environment |
| Run | One execution of a monitor, with per-step results and evidence |
| Deployment | A release event associated with an environment |
| Incident | Deduplicated, stateful failure record with a timeline |

## Security notes

- URLs supplied by users are validated against SSRF (scheme, destination IP, DNS, redirects).
  Set `ALLOW_PRIVATE_URLS=true` only in isolated local development.
- Tenant isolation is enforced server-side on every query; never trust a client-provided
  workspace/project identifier without a membership check.
- Browser workloads run in isolated workers; see
  `docs/master-plan/release-guardian/08-SECURITY-AND-THREAT-MODEL.md`.

## Planning status

The design docs under `docs/master-plan/release-guardian/` describe the full intended product.
This repository currently implements the engineering foundation (Phase B) and the first vertical
slice of identity, projects, environments, monitors, runs, deployments, and incidents.
