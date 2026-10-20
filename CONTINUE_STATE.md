# Continue State — 2026-10-20

## Repo state
- Working dir: `/home/mithleshkumardas/Documents/Release Guardian`
- Branch: `main`
- Remote: `git@github.com:livelyfun/Release-Guardian.git`
- Latest commit: `git log -1`
- Backend tests: 84 passed, 1 warning
- Backend lint: `cd backend && .venv/bin/ruff check app tests`
- Scripts lint: `backend/.venv/bin/ruff check scripts --config backend/pyproject.toml`
- Frontend: lint, `tsc --noEmit`, and `npm run build` pass
- Secret scan: `cd backend && .venv/bin/python -m app.services.secret_scanner` exits 0
- Local load test: 40 reads + 40 runs, 0 errors, 40/40 runs passed (see
  `docs/operations/LOAD-AND-RESILIENCE.md`)

## Implemented
- Identity/workspaces, projects/environments, roles, audit, API keys (hashed, revocable).
- Alembic migration `a65a1c13f47e` adds artifacts, escalation rules, and AI config.
- HTTP, Playwright browser, and Lighthouse checks; browser route-level SSRF guard;
  final-page screenshot artifacts; Lighthouse scores/thresholds/report artifacts.
- Runs (inline/Celery), scheduler with Redis lock, admission control, stale-run
  sweeper, per-run execution lock, retries/time limits, manual/deployment triggers.
- Baselines/regression detection, incident lifecycle, signed webhook and email
  adapters, escalation ladder with CRUD API and scheduled retries, and
  notification retry backoff/jitter with a per-attempt cap, maintenance
  windows, and consecutive-failure thresholds.
- Dashboard shows usage totals, artifact previews, escalation rules, and
  maintenance windows; run detail links signed evidence.
- Browser workers can optionally capture Playwright traces, HAR files, and
  per-step screenshots in addition to the final screenshot.
- Browser and Lighthouse runs are routed to dedicated Celery queues consumed
  by an isolated `browser-worker` compose service; Postgres pool sizing is
  configurable; an hourly task prunes artifacts past the retention window.
- Artifacts in S3-compatible storage; ownership is checked (artifact → run →
  environment → project) before issuing a 15-minute signed URL.
- Usage metering by kind (`runs`, `browser_checks`, `lighthouse_checks`).
- `AIConfiguration` structure (no AI execution/evaluation yet).
- M8 observability: JSON logs + request IDs, `/health`, `/ready`, `/metrics`
  (optional bearer token), SLO/alert docs, 14 runbooks.
- M8 tooling: load test + fixture, worker-restart drill, backup/restore drill,
  rollback procedure, cost model, production config guard, security review.
- Hardening: Redis rate limiting with fallback, Redis AOF, non-root API/worker,
  dropped capabilities, PID/tmpfs limits, secret scanner, artifact URL TTL.

## Not done / next targets
1. **M8 sign-off (primary):** run load, backup/restore, and rollback drills in
   staging; record evidence in the checklist; external penetration test;
   egress-firewall verification. See `docs/operations/PRODUCTION-CHECKLIST.md`.
2. M4: Playwright traces/HAR and step-level screenshots; artifact redaction.
3. M5: previous-known-good comparison, CI status checks, regression suppressions.
4. M6: maintenance windows, notification retry/backoff, real email transport.
5. M7: visual test builder, exports, team management UI, CLI.
6. I: AI assistance + evaluation harness, analytics, billing plans, regions.

## Quick commands
- `cd "/home/mithleshkumardas/Documents/Release Guardian"`
- `backend/.venv/bin/pytest -q`
- `cd backend && .venv/bin/ruff check app tests`
- `cd frontend && npm run lint && npm run typecheck && npm run build`
- `make security-scan`
- `make load-test` (requires API on `:8010`)
- `make drill-backup` (requires compose Postgres)
- `make drill-resilience` (requires compose stack with `WORKER_MODE=celery`)
- `git status --short && git log --oneline -1`

## Environment notes
- Backend venv: `backend/.venv` (Python 3.12, managed by uv; no pip binary).
- `boto3` is optional (`HAS_BOTO3`); artifact uploads fail gracefully if absent.
- Playwright browsers may be unavailable locally; browser checks return evidence
  rather than crashing.
- Lighthouse CLI must be on `PATH` for Lighthouse checks.
- Local rate limits are low by default; raise them for load tests.
- The fixture target rejects loopback unless `ALLOW_PRIVATE_URLS=true`.

## Files to inspect first
- `docs/operations/PRODUCTION-CHECKLIST.md` — M8 gate and outstanding evidence.
- `docs/operations/LOAD-AND-RESILIENCE.md` — drills and local baseline.
- `docs/operations/SLI-SLO.md` — metrics queries and alerts.
- `backend/app/workers/tasks/checks.py` — run lifecycle, locks, artifacts.
- `backend/app/workers/tasks/maintenance.py` — stale-run recovery.
- `backend/app/services/capacity.py` — admission control.
- `docs/master-plan/release-guardian/14-IMPLEMENTATION-ROADMAP.md` — authoritative status.
