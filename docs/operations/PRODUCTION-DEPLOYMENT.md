# Production deployment

Deployment of Release Guardian to Vercel (frontend) and Render (API, Celery
workers, PostgreSQL, Key Value). Written to be executed top to bottom; each
step names the exact failure it prevents.

**Status as of 2026-10-20: partially deployed.** The frontend is live; the
backend stack is blocked on account-level actions that require a browser
session (see [Blockers](#blockers)). No secret values appear in this document.

Decisions taken on 2026-10-20:

- **Compute spend deferred.** Render background workers require a payment
  method. The API, Celery worker, browser worker, and scheduler are deliberately
  **not provisioned**; this document is the ready-to-run specification for when
  budget is approved.
- **Artifacts disabled.** Cloudflare R2 is not enabled on the account, so
  `S3_BUCKET` stays empty. Runs still execute and record upload failures as
  evidence; artifact links are empty.
- **Git access in progress.** The Render GitHub App is being installed for the
  private repository so the service definitions below can be created without
  further changes.

## Deployed topology

```
Browser
  │
  ├─ https://release-guardian.vercel.app        Vercel, Next.js (App Router)
  │      NEXT_PUBLIC_API_URL baked at build time
  │
  └─ https://release-guardian-api.onrender.com  Render web service (NOT YET CREATED)
         │
         ├─ PostgreSQL 16   dpg-dbbi0aff3r2c738vbb10-a  (created, available)
         ├─ Key Value        red-dbbi0ajbc2fs73b98v80  (created, available)
         ├─ celery worker    queue `release_guardian`  (not created)
         ├─ browser worker   queues `browser`, `lighthouse`  (not created)
         └─ celery beat      drifts monitor schedules  (not created)
```

All Render resources are in region `oregon`, matching PostgreSQL 16 from
`docker-compose.yml`.

## What is live

| Component | Identifier | State |
|---|---|---|
| Vercel project | `prj_jKowhpNNRVNz9wufgXr600vs63sl` | configured, Git-connected |
| Production domain | `https://release-guardian.vercel.app` | **live, HTTP 200** |
| Production build | commit `114e695` (`main`) | READY, promoted |
| Render PostgreSQL | `dpg-dbbi0aff3r2c738vbb10-a` | available, free, expires 2026-11-19 |
| Render Key Value | `red-dbbi0ajbc2fs73b98v80` | available, free, in-memory only |
| Render compute services | — | **none created** |
| Cloudflare R2 bucket | — | **not enabled on account** |

### Vercel settings

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework | Next.js |
| Node.js | `24.x` (the account rejects `20.x` as discontinued) |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `.next` |

`NEXT_PUBLIC_API_URL=https://release-guardian-api.onrender.com/api/v1` is set
for Production and Preview. It is inlined into the client bundle at build time,
so changing it requires a redeploy, not a restart.

Git-connected deploys are enabled: every push to `main` produces a production
deployment. Verified from the build artifacts — the API URL is present in the
served chunks.

## Render service definitions

Create these four services from the same Git repository. All four need the
Render GitHub App installed on the repository (see Blockers).

| Service | Type | Dockerfile | Plan | Start command / command |
|---|---|---|---|---|
| `release-guardian-api` | web | `backend/Dockerfile` | `0.5c-512mb` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `release-guardian-worker` | background worker | `backend/Dockerfile.worker` | `0.5c-512mb` | `celery -A app.workers.celery_app.celery_app worker -Q release_guardian --concurrency=2 --loglevel=info` |
| `release-guardian-browser` | background worker | `backend/Dockerfile.worker` | `1c-2g` | `celery -A app.workers.celery_app.celery_app worker -Q browser,lighthouse --concurrency=2 --loglevel=info` |
| `release-guardian-scheduler` | background worker | `backend/Dockerfile` | `0.5c-512mb` | `celery -A app.workers.celery_app.celery_app beat --loglevel=info` |

Notes:

- **Docker context is `backend/`**, so `dockerfilePath` is `./Dockerfile` and
  `dockerContext` is `./backend` (Render resolves both against the repository
  root when set through the API as `backend/Dockerfile` plus
  `dockerContext: ./backend`).
- The API must bind `$PORT`. Render injects `PORT` (default 10000); the image
  default hardcodes 8000 and will fail the health check otherwise.
- Health check path: `/health`. Readiness (`/ready`) checks Redis and the
  database and is the better signal once Key Value is reachable.
- The scheduler is a **background worker**, not a cron job: `celery beat` must
  stay resident to hold the schedule. Duplicate schedulers are safe — the
  existing Redis lock in `app/services/locks.py` prevents double dispatch.
- `Dockerfile.worker` carries Playwright plus the Lighthouse CLI and
  `CHROME_PATH=/usr/local/bin/chrome`; the browser worker is the only service
  that needs it.

### Migrations

The API owns schema changes; nothing else migrates.

- API `preDeployCommand`: `alembic upgrade head`. This runs once per deploy
  before traffic shifts, so a failed migration blocks the release.
- Workers and the scheduler must **not** run Alembic. Concurrent
  `upgrade head` from four services races on the version table.
- Alembic head is `0eb1856e2764` (chain: `d2b26372f7ff` → `084556d3ce82` →
  `a65a1c13f47e` → `9e8925d39560` → `0eb1856e2764`).
- Free PostgreSQL expires 30 days after creation with no backups. Upgrade to a
  paid plan or take `pg_dump` backups before 2026-11-19.

### Environment variables

Shared by all four services unless noted. Names come from
`backend/app/core/config.py`; `ENVIRONMENT=production` activates the startup
guard in `backend/app/core/production.py`, which refuses to boot on a default
JWT secret, a short webhook secret, SQLite, `ALLOW_PRIVATE_URLS=true`, or a
wildcard CORS origin.

| Variable | Value / source |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Render PostgreSQL **internal** URL, `postgresql+psycopg://…` |
| `DB_POOL_SIZE` | `5` |
| `DB_MAX_OVERFLOW` | `5` |
| `REDIS_URL` | Render Key Value **internal** URL |
| `JWT_SECRET` | generated, ≥32 characters |
| `WEBHOOK_SIGNING_SECRET` | generated, ≥16 characters |
| `CORS_ORIGINS` | `["https://release-guardian.vercel.app"]` |
| `ALLOW_PRIVATE_URLS` | `false` (never enable in production) |
| `WORKER_MODE` | `celery` |
| `RATE_LIMIT_BACKEND` | `redis` |
| `METRICS_ENABLED` | `true` |
| `READINESS_CHECK_REDIS` | `true` |
| `S3_BUCKET` | empty — artifact storage disabled until R2 exists |
| `NEXT_PUBLIC_API_URL` | Vercel only |

**Pool sizing matters.** `DB_POOL_SIZE=5` and `DB_MAX_OVERFLOW=5` cap each
service at 10 connections. Three compute services plus the API stay well under
Render's 100-connection limit; the defaults (10 + 20 = 30 each) would exhaust it
and produce `too many connections` errors under load.

Leave `S3_BUCKET` empty until R2 is enabled. Artifact upload failures are
captured as run evidence rather than failing the run, so the product degrades
instead of breaking.

Optional integrations, only if used: `SMTP_*` (email notifications),
`GITHUB_STATUS_TOKEN` (commit statuses), `METRICS_TOKEN` (protects `/metrics`).

Generate secrets without echoing them into shell history:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Smoke checks

Run after every deploy. Replace the API host once the service exists.

| Check | Command | Expected |
|---|---|---|
| Frontend root | `curl -s -o /dev/null -w '%{http_code}' https://release-guardian.vercel.app/` | `200` |
| Frontend title | `curl -s https://release-guardian.vercel.app/ \| grep -o '<title>[^<]*'` | `Release Guardian` |
| API URL baked in | grep the served `/_next/static/chunks/*.js` for `onrender.com` | the configured host |
| API liveness | `curl -s https://release-guardian-api.onrender.com/health` | `{"status":"ok"}` |
| API readiness | `curl -s https://release-guardian-api.onrender.com/ready` | `200`, database and Redis ok |
| Auth | `POST /api/v1/auth/register` then `POST /api/v1/auth/login` | token pair |
| Run path | create project → environment → monitor → run | run reaches `succeeded` |

Verified on 2026-10-20: frontend `/`, `/login`, `/dashboard`, `/projects`,
`/incidents` all return `200`, title renders, and the API URL is present in the
served bundle. `/register` returns `404` because registration lives on
`/login`. The API checks cannot pass yet — no Render service exists.

## Blockers

Each of these needs a browser session on an account we cannot authenticate as.

### 1. Render cannot read the private repository

Symptom, on service creation:

```
400 passed in repository URL is invalid or unfetchable:
    https://github.com/livelyfun/Release-Guardian
```

The repository is private and no Git provider is connected to the Render
account. This blocks **all** Render compute services.

Fix: install the Render GitHub App and grant it access to this repository.

<https://github.com/apps/render/installations/new>

Then retry the service creation in the Render dashboard, or through the API
using the service definitions above.

### 2. Background workers require a payment method

```
402 Payment information is required
```

Free Render compute covers web services, PostgreSQL, Key Value, and static
sites only. `background_worker` and `cron_job` are paid. The Celery worker,
browser worker, and scheduler cannot be created on the free plan.

**Spend is intentionally deferred**, so these three services are not created.
When budget is approved, add a payment method and create them on the plans
listed above — no other change is needed.

### 3. Cloudflare R2 is not enabled

```
wrangler r2 bucket list → code 10042
Please enable R2 through the Cloudflare Dashboard
```

Fix: enable R2 in the Cloudflare dashboard, create a bucket, then set
`S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and
`S3_REGION=auto` on the API and both workers. Until then artifacts are
unavailable and the corresponding evidence links are empty.

### 4. Key Value external access is IP-allowlisted

Connecting to the Key Value external URL from a local machine returns
`Client IP address is not in the allowlist`. This only affects local
verification; services inside Render use the internal URL and are unaffected.
Do not widen the allowlist to `0.0.0.0/0` to work around it.

### 5. PostgreSQL external TLS

Direct `psql`/psycopg connections to the external hostname fail the TLS
handshake from this workstation (`SSL connection has been closed unexpectedly`)
even though the certificate chain is valid. Run migrations from inside Render
via the API `preDeployCommand` instead of from a laptop. This does not affect
the deployed services, which use the internal URL.

## Cost

| Resource | Plan | Monthly |
|---|---|---|
| Vercel | Pro | $20 |
| Render web service | `0.5c-512mb` | $7 |
| Render worker | `0.5c-512mb` | $7 |
| Render browser worker | `1c-2g` | $25 |
| Render scheduler | `0.5c-512mb` | $7 |
| Render PostgreSQL | `0.5c-1g` | $19 |
| Render Key Value | `256mb` | $10 |
| Cloudflare R2 | usage-based | ~$0 at this volume |
| **Total** | | **~$95/mo** |

Currently billed: $0. The free PostgreSQL and Key Value instances exist but are
not backed by a payment method; the free PostgreSQL instance expires
2026-11-19.

## Rollback

- **Frontend:** `vercel rollback` promotes the previous production deployment.
  Any commit on `main` is a valid target — builds are reproducible from Git.
- **API:** Render keeps previous deploys; "Rollback" redeploys the prior image.
  Migrations are forward-only, so roll back only across schema-compatible
  commits.
- **Database:** no automated backups on the free plan. Take `pg_dump` before
  any deploy that includes a migration.
