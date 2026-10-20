# Production deployment

How to run Release Guardian outside a developer laptop. Two supported paths:

1. **Single host with Docker Compose** — recommended for self-hosting.
2. **Managed platform** — separate web service, background workers, PostgreSQL,
   and Redis (any provider that can build a Dockerfile and run long-lived
   processes).

This repository does **not** ship a hosted instance. Every hostname below is a
placeholder; substitute your own.

## Topology

```
Browser
  │
  ├─ https://app.example.com          Next.js dashboard (static/SSR)
  │      NEXT_PUBLIC_API_URL baked at build time
  │
  └─ https://api.example.com          FastAPI control plane
         │
         ├─ PostgreSQL 16+            durable state
         ├─ Redis                     broker, rate limits, scheduler lock
         ├─ worker                    queue `release_guardian`
         ├─ browser worker            queues `browser`, `lighthouse`
         └─ scheduler                 `celery beat`
```

The dashboard and the API are separate origins. Set `CORS_ORIGINS` on the API
to the dashboard origin exactly; do not use a wildcard.

## Path 1 — Docker Compose (single host)

`docker-compose.yml` defines `postgres`, `redis`, `api`, `worker`,
`browser-worker`, and `scheduler`. It is the reference deployment.

```bash
cp .env.example .env          # then edit every value
# Set at minimum: JWT_SECRET, WEBHOOK_SIGNING_SECRET, CORS_ORIGINS,
# ENVIRONMENT=production, and the database/Redis credentials.
docker compose up -d --build
```

The `api` service runs `alembic upgrade head` before starting Uvicorn, so the
schema is current on first boot and after every upgrade. The other services
must never run migrations.

Put a TLS-terminating reverse proxy (or the platform's load balancer) in front
of the API and the dashboard, and forward `X-Forwarded-For` / `X-Forwarded-Proto`
so request logging and rate limiting see client addresses.

## Path 2 — Managed platform

The shape below is provider-neutral; the exact field names differ per platform.
Create four compute resources from this repository:

| Service | Build | Plan sizing | Command |
|---|---|---|---|
| `api` | `backend/Dockerfile` (context `backend/`) | 0.5 vCPU / 512 MB | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `worker` | `backend/Dockerfile.worker` (context `backend/`) | 0.5 vCPU / 512 MB | `celery -A app.workers.celery_app.celery_app worker -Q release_guardian --concurrency=2 --loglevel=info` |
| `browser-worker` | `backend/Dockerfile.worker` (context `backend/`) | 1 vCPU / 2 GB | `celery -A app.workers.celery_app.celery_app worker -Q browser,lighthouse --concurrency=2 --loglevel=info` |
| `scheduler` | `backend/Dockerfile` (context `backend/`) | 0.5 vCPU / 512 MB | `celery -A app.workers.celery_app.celery_app beat --loglevel=info` |

Notes:

- **Build context is `backend/`.** Set the Dockerfile path relative to the
  repository root (`backend/Dockerfile`) and the context to `backend/`.
- **Bind `$PORT`.** Most platforms inject a `PORT` variable; the image default
  hardcodes 8000 and will fail the health check if you do not override it.
- **Health check:** `/health` for liveness. `/ready` additionally checks the
  database and Redis and is the better readiness signal.
- **The scheduler is a long-lived process, not a cron job.** `celery beat` must
  stay resident. Running more than one is safe: the Redis lock in
  `app/services/locks.py` prevents double dispatch.
- **The browser worker needs Playwright browsers plus the Lighthouse CLI.**
  `Dockerfile.worker` installs both and sets `CHROME_PATH`.
- Background workers and cron jobs are paid features on several platforms even
  when web services have a free tier. Budget for three workers.

### Object storage (optional)

Screenshots, traces, HAR files, and Lighthouse reports are stored in any
S3-compatible bucket. Without it, runs still execute and record upload failures
as evidence; artifact links are simply empty.

```env
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_BUCKET=<bucket>
S3_ACCESS_KEY=<key>
S3_SECRET_KEY=<secret>
S3_REGION=auto
S3_USE_SSL=true
```

Keep the bucket private and serve artifacts only through the API's signed URLs.

## Migrations

The API owns schema changes; nothing else migrates.

- Run `alembic upgrade head` once, before the new API revision takes traffic
  (a platform "pre-deploy command", an init container, or the Compose `api`
  entrypoint).
- Workers and the scheduler must **not** run Alembic. Concurrent upgrades race
  on the version table.
- Migrations are forward-only. Roll back application code only across commits
  that are schema-compatible.

## Environment variables

Names come from `backend/app/core/config.py`. `ENVIRONMENT=production`
activates the startup guard in `backend/app/core/production.py`, which refuses
to boot on a default JWT secret, a short webhook secret, SQLite,
`ALLOW_PRIVATE_URLS=true`, or a wildcard CORS origin.

| Variable | Value / source |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | `postgresql+psycopg://…` — never SQLite |
| `DB_POOL_SIZE` | `5` |
| `DB_MAX_OVERFLOW` | `5` |
| `REDIS_URL` | `redis://…` or `rediss://…` |
| `JWT_SECRET` | generated, ≥32 characters |
| `WEBHOOK_SIGNING_SECRET` | generated, ≥16 characters |
| `CORS_ORIGINS` | `["https://app.example.com"]` — exact origin, never `*` |
| `ALLOW_PRIVATE_URLS` | `false` in any internet-facing deployment |
| `WORKER_MODE` | `celery` |
| `RATE_LIMIT_BACKEND` | `redis` |
| `METRICS_ENABLED` | `true` |
| `METRICS_TOKEN` | set it, or `/metrics` is public |
| `READINESS_CHECK_REDIS` | `true` |
| `S3_*` | only if artifact storage is configured |
| `NEXT_PUBLIC_API_URL` | dashboard build only, e.g. `https://api.example.com/api/v1` |

**Pool sizing.** Each service owns its own pool. With four services, the defaults
(`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`) can exhaust a small managed database's
connection limit and produce `too many connections` under load. `5` + `5` caps
each service at ten connections.

`NEXT_PUBLIC_API_URL` is inlined into the client bundle at build time. Changing
it requires rebuilding the dashboard, not restarting it.

Generate secrets without writing them into shell history:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Network isolation and SSRF (self-host requirement)

Release Guardian fetches URLs supplied by its users. That is inherently an SSRF
surface. The application validates scheme, host, and resolved address, re-checks
every redirect hop, and intercepts browser subrequests, but application-layer
checks alone are not sufficient against DNS rebinding (resolve-time validation,
connect-time re-resolution).

If you expose Release Guardian to untrusted users, you **must** also:

1. Run the workers in a network that cannot reach your metadata service
   (`169.254.169.254`), the control plane's private network, or internal
   administrative interfaces.
2. Apply an egress firewall that allows only public HTTP/HTTPS, and prefer
   connection-time IP filtering so a rebinding answer cannot reach a private
   address.
3. Keep `ALLOW_PRIVATE_URLS=false`. It exists for local fixtures and tests only.

Self-hosters who skip this are running an open proxy with extra steps.

## Smoke checks

Replace the hosts with your own.

| Check | Command | Expected |
|---|---|---|
| API liveness | `curl -s https://api.example.com/health` | `{"status":"ok"}` |
| API readiness | `curl -s https://api.example.com/ready` | `200`, database and Redis ok |
| Dashboard | `curl -s -o /dev/null -w '%{http_code}' https://app.example.com/` | `200` |
| API URL baked in | inspect the served `/_next/static/chunks/*.js` | your API host |
| Auth | `POST /api/v1/auth/register`, then `POST /api/v1/auth/login` | token pair |
| Run path | create project → environment → monitor → run | run reaches `succeeded` |
| Browser path | run a browser check | screenshots/evidence recorded, or a clear storage error |

## Rollback

- **Dashboard:** redeploy the previous build. Any commit on your release branch
  is a reproducible target.
- **API and workers:** redeploy the previous image and restart the workers so
  they pick up the older task signatures.
- **Database:** take a `pg_dump` before any deploy that includes a migration.
  Managed free tiers often provide no backups and expire on a fixed schedule.
