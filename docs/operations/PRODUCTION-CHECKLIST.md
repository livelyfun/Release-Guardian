# Production Go-Live Checklist

Use this as the gate for M8. A checked box requires a link or command output as
evidence; a local test does not satisfy a staging/production requirement.

## Current status

| Area | Status | Evidence |
|---|---|---|
| Observability (`/metrics`, `/ready`, JSON logs) | Implemented | `backend/app/main.py`, `core/metrics.py`, `core/observability.py` |
| SLOs and alerts | Documented, not validated in staging | [SLI-SLO.md](SLI-SLO.md) |
| Runbooks | Documented | [RUNBOOKS.md](RUNBOOKS.md) |
| Load test | Tooling + local baseline | [LOAD-AND-RESILIENCE.md](LOAD-AND-RESILIENCE.md) |
| Resilience drills | Tooling + unit tests; staging drill pending | `scripts/resilience_drill.py` |
| Backup/restore | Tooling; staging drill pending | [BACKUP-RESTORE.md](BACKUP-RESTORE.md) |
| Rollback drill | Procedure; staging drill pending | [BACKUP-RESTORE.md](BACKUP-RESTORE.md) |
| Security review | Self-review complete; external test pending | [SECURITY-REVIEW.md](SECURITY-REVIEW.md) |
| Cost validation | Model complete; prices/volumes pending | [COST-VALIDATION.md](COST-VALIDATION.md) |
| Local verification (tests, migrations, guard, smoke) | Complete for local scope | [evidence/local-verification-2026-10-20.md](evidence/local-verification-2026-10-20.md) |

**M8 is not signed off until every unchecked item below is complete.**

## 1. Configuration and secrets

- [ ] `ENVIRONMENT=production`.
- [ ] `JWT_SECRET` ≥ 32 random chars, stored in a secret manager.
- [ ] `WEBHOOK_SIGNING_SECRET` ≥ 16 random chars, stored in a secret manager.
- [ ] `DATABASE_URL` points to managed Postgres, not SQLite.
- [ ] `ALLOW_PRIVATE_URLS=false`.
- [ ] `CORS_ORIGINS` contains only real frontend origins (no `*`).
- [ ] `METRICS_TOKEN` set or `/metrics` restricted at the network edge.
- [ ] S3 credentials are least-privilege and scoped to the artifacts bucket.
- [ ] Startup succeeds with the production guard
      (`python -c "from app.core.config import settings; from app.core.production import validate_production_settings as v; v(settings)"`).

## 2. Data and recovery

- [ ] Managed Postgres with PITR enabled; RPO ≤ 15 min verified.
- [ ] Daily snapshots retained per policy; restore into a scratch instance
      succeeds.
- [ ] `scripts/backup_restore_drill.sh` passes against staging.
- [ ] Redis runs with AOF and a persistent volume.
- [ ] S3 bucket private, public access blocked, versioning/lifecycle enabled.
- [ ] Artifact retention rule verified (objects deleted after the configured
      window).
- [ ] Rollback drill passes in ≤ 15 min with a tested previous image.

## 3. Security

- [ ] Egress allowlist enforced for API and browser workers (SSRF residual R1).
- [ ] Browser workers on dedicated nodes; non-root, caps dropped,
      `no-new-privileges`, tmpfs, PID limit.
- [ ] TLS on every public endpoint; HSTS at the edge.
- [ ] Dependency/image scanning enabled; no unresolved high/critical findings.
- [ ] Secret scan clean: `python -m app.services.secret_scanner`.
- [ ] Cross-tenant negative tests pass in CI.
- [ ] SSRF matrix tests pass (loopback/private/link-local/metadata/redirect/
      IPv6/browser subresource).
- [ ] External penetration test complete; findings triaged.
- [ ] Token/credential rotation procedure tested.

## 4. Observability and alerting

- [ ] Prometheus scrapes every API replica; metrics counter aggregation verified.
- [ ] Dashboards exist for availability, latency, run integrity, scheduler
      freshness, queue depth/age, notification and artifact failure rates.
- [ ] Alerts from [SLI-SLO.md](SLI-SLO.md) routed to the on-call channel.
- [ ] `/ready` is the load-balancer health check; `/health` is liveness only.
- [ ] Logs are collected with `request_id`, retention set, and no secrets.
- [ ] A synthetic canary runs outside the platform and checks `/health`,
      `/ready`, and a real monitor run (meta-monitoring).

## 5. Reliability and capacity

- [ ] Staging load test meets the gates in
      [LOAD-AND-RESILIENCE.md](LOAD-AND-RESILIENCE.md).
- [ ] Worker count sized for peak with 1.5–2× headroom.
- [ ] `MAX_ACTIVE_RUNS_PER_WORKSPACE` and per-monitor limits tuned for the
      largest tenant.
- [ ] Scheduler runs as a singleton (or lock verified across replicas).
- [ ] Stale-run sweeper runs every minute; timeout and re-dispatch counts
      observed during the drill.
- [ ] Database connection pool sized below the provider limit.
- [ ] Browser/Lighthouse worker pool isolated from HTTP checks.

## 6. Product behavior

- [ ] A new user can register, create a project/environment/monitor, trigger a
      run, and see evidence without API calls.
- [ ] Failed checks open one incident; recovery resolves it; notifications are
      delivered with a verifiable signature.
- [ ] Deployment-triggered runs mark the deployment passed/failed/inconclusive.
- [ ] Baseline regression detection produces the expected incident.
- [ ] Usage endpoint reports per-kind counts for the workspace.
- [ ] API key creation/revocation works and keys inherit the intended role.

## 7. Cost and operations

- [ ] Provider prices entered into `scripts/cost_model.py`; forecast approved.
- [ ] Budget alerts at 50/80/100% of forecast.
- [ ] Artifact and log retention configured.
- [ ] On-call rotation, escalation contacts, and incident channel confirmed.
- [ ] All 14 runbooks reviewed by the on-call engineer.
- [ ] Status page/communication template ready.

## 8. Release and post-release

- [ ] Migration is expand/contract and tested against a production-like dump.
- [ ] `alembic current` matches the release; downgrade tested if applicable.
- [ ] Previous image digest recorded for rollback.
- [ ] Deploy to staging; run the full smoke suite; observe for 24 hours.
- [ ] Deploy to production during a low-traffic window with the rollback owner
      present.
- [ ] Post-deploy: `/ready` 200, error rate and latency within SLO, scheduler
      tick fresh, a real run passes.
- [ ] Dogfood: add Release Guardian's own staging/production URLs as monitors and
      let it verify the next deploy.
- [ ] Record actual RPO/RTO and load results; update SLOs if reality differs.

## Sign-off

| Role | Name | Date | Signature/approval link |
|---|---|---|---|
| Engineering owner | | | |
| Security reviewer | | | |
| Operations/on-call | | | |
| Product owner | | | |
