# Local Verification — 2026-10-20

**Revision:** `33ff680` (backend, worker, frontend, migrations)
**Environment:** Developer workstation, Python 3.12, Node 20+, SQLite,
`WORKER_MODE=inline`. Docker daemon was unavailable, so no Postgres/Redis
containers were started.

This report covers checks that can be reproduced locally. It is **not** staging
evidence and does not satisfy the M8 sign-off gates in
[`../PRODUCTION-CHECKLIST.md`](../PRODUCTION-CHECKLIST.md).

## Code quality

| Command | Result |
|---|---|
| `backend/.venv/bin/ruff check app tests` | Pass |
| `backend/.venv/bin/pytest -q` | **98 passed**, 1 deprecation warning |
| `backend/.venv/bin/ruff check scripts --config backend/pyproject.toml` | Pass |
| `bash -n scripts/backup_restore_drill.sh` | Pass |
| `cd frontend && npm run lint` | Pass, no warnings |
| `cd frontend && npm run typecheck` | Pass |
| `cd frontend && npm run build` | Pass, 14 routes generated |
| `cd docker-compose.yml && docker compose config` | Parses (daemon unavailable) |

## Security

Secret scan (`backend/.venv/bin/python -m app.services.secret_scanner`):

```json
{
  "environment_variables_scanned": 86,
  "configuration_values_scanned": 57,
  "findings_count": 0,
  "is_secure": true
}
```

Production guard, safe configuration (exit 0, prints `production guard: ok`):

```bash
ENVIRONMENT=production \
JWT_SECRET=<48 chars> \
WEBHOOK_SIGNING_SECRET=<32 chars> \
DATABASE_URL=postgresql+psycopg://user:pass@db:5432/rg \
ALLOW_PRIVATE_URLS=false \
CORS_ORIGINS='["https://app.example.com"]' \
python -c "from app.core.config import settings; from app.core.production import validate_production_settings as v; v(settings)"
```

Unsafe configuration (`ENVIRONMENT=Production`, default secrets, SQLite,
private URLs, wildcard CORS) exits 1 with:

```text
RuntimeError: Refusing to start in production with unsafe configuration:
JWT_SECRET must be overridden with a strong random value; WEBHOOK_SIGNING_SECRET
must be overridden; DATABASE_URL must use a production database, not SQLite;
ALLOW_PRIVATE_URLS must be false in production; CORS_ORIGINS must not allow
every origin
```

Cross-tenant tests cover artifact signed URLs, resources, API keys, runs, and
incidents. SSRF tests cover loopback, private, link-local/metadata, IPv4/IPv6,
unsupported schemes, DNS resolution, and each redirect hop.

## Database and migrations

Fresh SQLite database:

```bash
alembic upgrade head        # ok
alembic downgrade -1        # ok
alembic upgrade head        # ok
alembic check               # No new upgrade operations detected.
alembic current             # 0eb1856e2764 (head)
```

The chain includes the artifacts/escalation/AI tables, notification retry
fields, and maintenance windows.

## Runtime smoke test

`uvicorn app.main:app` on `127.0.0.1:8011` with SQLite:

```text
GET /health -> 200
{"status":"ok","service":"Release Guardian","version":"0.1.0",
 "environment":"development","worker_mode":"inline"}

GET /ready -> 200
{"status":"ready","checks":{"database":"ok"}}

GET /metrics -> 200 text/plain
rg_api_requests_total{method="GET",route="/health",status="200"} 2
```

The smoke response also carried `x-request-id`, `x-content-type-options:
nosniff`, `x-frame-options: DENY`, and `referrer-policy: no-referrer`.

## Load baseline

Tooling validation only, re-run on the current revision: 40 reads at 115.8 rps
(p95 90.4 ms) and 40 runs at 22.4 rps (p95 577.1 ms, p99 917.8 ms, 40/40
passing), 0% errors across 80 requests on a single inline API process.
Raw report: [`loadtest-local-2026-10-20.json`](loadtest-local-2026-10-20.json).
See [`../LOAD-AND-RESILIENCE.md`](../LOAD-AND-RESILIENCE.md) for the staging
gates.

## Feature coverage added since the previous report

- Workspace team management (invite, role changes, removal, last-owner
  safeguards) with API and settings UI.
- Browser journey step builder (create/edit), trace/HAR/per-step screenshot
  options, Lighthouse form-factor/report controls.
- CSV exports for runs and incidents, plus `scripts/rg.py` CLI smoke-checked
  with `--help`/ruff.
- Deployment comparison, regression suppressions, SMTP email transport, and
  GitHub commit statuses (mocked tests; no live provider calls).
- HAR credential redaction and URL query redaction.

## Not covered locally

- Postgres backup/restore drill (`scripts/backup_restore_drill.sh`): no Docker
  or Postgres available.
- Worker kill/restart resilience drill: no Redis/Celery stack.
- Rollback/image digest drill: no registry or previous image.
- Staging SLOs, 24-hour soak, Prometheus scrape/alert routing.
- External penetration test, egress firewall verification, TLS/HSTS at the edge.
- Real Playwright trace/HAR paths (Playwright is absent from this venv; the
  capture code is unit-tested only through artifact metadata).
