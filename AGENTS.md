# AGENTS.md

## Project

Release Guardian — multi-tenant website reliability, synthetic monitoring, and release
verification. Design docs live in `docs/master-plan/release-guardian/`.

## Layout

- `backend/` — FastAPI control plane, SQLAlchemy models, Celery workers, Alembic migrations, pytest.
- `frontend/` — Next.js (App Router) + TypeScript + Tailwind dashboard.
- `docs/master-plan/` — product, architecture, security, and operations plans.
- `.github/workflows/ci.yml` — backend lint/tests and frontend lint/typecheck/build.

## Commands

Run from the repository root unless noted.

- `make install` — install backend and frontend dependencies.
- `make up` — start local Postgres and Redis via Docker Compose.
- `make migrate` — apply Alembic migrations (`backend/alembic`).
- `make test` — backend pytest suite.
- `make lint` — ruff (backend) and Next.js ESLint (frontend).
- `make dev-api` — FastAPI on `http://localhost:8000` (docs at `/docs`).
- `make dev-worker` — Celery worker; `make dev-scheduler` — Celery beat.
- `make dev-web` — Next.js on `http://localhost:3000`.

Backend venv used in this environment: `backend/.venv` (Python 3.12).
Invoke tools as `backend/.venv/bin/pytest`, `backend/.venv/bin/ruff`, etc.

## Conventions

- Python 3.11+ (CI uses 3.12), Ruff lint (`E,F,I,B,UP`; `B008` ignored for FastAPI `Depends`).
- TypeScript strict; path alias `@/*` → `frontend/src/*`.
- Every tenant-scoped query must enforce workspace membership server-side
  (`app/api/v1/deps.py`, `app/api/v1/access.py`).
- User-supplied URLs pass through `app/services/url_guard.py` (SSRF defense) before execution.
- Errors use the structured envelope in `app/core/errors.py`.
- Do not commit secrets. `.env` is ignored; keep `.env.example` current.

## Implementation status

Engineering foundation and vertical slices are implemented: identity/workspaces,
projects/environments, monitors, runs (inline/Celery), the due-monitor scheduler,
deployment-triggered runs, latency baselines and regression detection, incidents with
webhook notification attempts, API keys, audit logs, and the dashboard. Remaining
master-plan phases (full Playwright/Lighthouse execution, artifact storage, escalation,
billing, AI assistance) are not yet built. See
`docs/master-plan/release-guardian/14-IMPLEMENTATION-ROADMAP.md`.
