# Runbooks

Each runbook follows the same shape: **detect → contain → investigate →
recover → verify → escalate**. Runbooks assume the Docker Compose service
names from `docker-compose.yml`; adjust for the managed platform.

## Global escalation

| Severity | Meaning | Notify | Response |
|---|---|---|---|
| SEV1 | Platform down or data/security risk | On-call + owner | Immediate, incident channel |
| SEV2 | Core workflow degraded (runs, alerts) | On-call | 15 min |
| SEV3 | Single tenant or non-critical feature | On-call (next business day) | 1 business day |

Before changing anything: record the start time, current deploy revision
(`git rev-parse HEAD`), and the dashboards/screens you used. Prefer reversible
actions. Never run destructive SQL against production without a verified
backup.

Useful commands:

```bash
docker compose ps
docker compose logs --tail=200 api
docker compose logs --tail=200 worker
docker compose logs --tail=200 scheduler
curl -s localhost:8000/health | jq
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/ready
curl -s localhost:8000/metrics | grep -E 'rg_(scheduler|pending|queue|stale)'
```

---

## 1. Website appears down

**Detect:** Multiple monitors fail at once; dashboard shows red runs; customers
report outages. Confirm the monitor target itself from outside the platform.

**Contain:** Do not disable monitors. If the *platform* cannot reach any
target, follow runbook 2/5 instead of treating it as a customer outage.

**Investigate:**
1. Open affected runs; inspect `summary.status_code`, redirect chain, and error.
2. Check DNS/TLS from a worker container:
   `docker compose exec worker python -c "import httpx; print(httpx.get('https://target.example', timeout=10).status_code)"`.
3. Determine scope: one tenant, one region, one target, or all targets.

**Recover:** If the target is down, keep monitoring and let incidents track it.
If the platform's outbound path is broken, fix egress/DNS (runbook 2).

**Verify:** Trigger a manual run for one affected monitor; confirm the incident
auto-resolves on the next successful check.

**Escalate:** Customer-facing SEV1 when a production target is down; SEV2 for a
single non-production environment.

---

## 2. Worker pool unavailable

**Detect:** `ApiHighErrorRate` with runs stuck `pending`; `rg_queue_depth`
growing; `docker compose ps` shows worker restarting/unhealthy; worker logs show
OOM, browser crashes, or connection errors.

**Contain:**
1. Scale the pool down to a known-good replica count.
2. Pause non-essential scheduled checks by disabling noisy monitors if the queue
   is saturating.
3. If the cause is a bad release, roll back the worker image (runbook 13).

**Investigate:**
```bash
docker compose logs --tail=300 worker | grep -iE 'error|traceback|oom|browser'
docker stats --no-stream
docker compose exec worker celery -A app.workers.celery_app.celery_app inspect active
```

**Recover:**
1. Restart the worker with a healthy image: `docker compose up -d --force-recreate worker`.
2. Confirm `celery inspect ping` responds.
3. The stale-run sweeper re-dispatches runs pending longer than
   `PENDING_RUN_TIMEOUT_SECONDS`; do not manually duplicate runs.

**Verify:** `/ready` is 200, `rg_queue_depth` drains, a manual run completes, and
no new `rg_stale_runs_total{action="timed_out"}` increments appear.

**Escalate:** SEV1 if all execution is unavailable; SEV2 if only browser or
Lighthouse workers are down (HTTP checks still work).

---

## 3. Queue backlog growing

**Detect:** `QueueBacklog` alert; `rg_pending_runs` above 50; oldest pending run
older than 300 s; workers healthy but not keeping up.

**Contain:** Reduce inbound work first — disable high-frequency monitors in the
affected workspace, lower deployment-trigger fan-out, or apply workspace
`MAX_ACTIVE_RUNS_PER_WORKSPACE`. Do not delete queued runs.

**Investigate:**
1. Compare `rg_queue_depth` with `rg_active_runs`: high depth + low active means
   too few workers or stuck workers.
2. Check per-kind duration (`rg_run_duration_seconds`) for a slow target/pattern.
3. Look for one tenant causing the spike via audit logs and monitor counts.

**Recover:** Add workers (horizontal scale) or roll back a slow release. If a
single target hangs, disable that monitor and let other work drain.

**Verify:** Depth falls steadily; p95 oldest age returns below 300 s; no new
timeouts in the sweeper.

**Escalate:** SEV2 if scheduled checks are delayed > 15 min; SEV1 if deployment
verification is blocked for a production release.

---

## 4. Scheduler stopped

**Detect:** `SchedulerStale` alert; no runs with `trigger="scheduled"` for
several intervals; `time() - rg_scheduler_last_success_timestamp_seconds > 300`;
scheduler logs show lock errors or crashes.

**Contain:** Start a single scheduler instance only. Multiple schedulers are
safe for correctness (Redis lock + active-run check) but can add noise.

**Investigate:**
```bash
docker compose logs --tail=200 scheduler
docker compose exec redis redis-cli GET rg:lock:scheduler
docker compose exec redis redis-cli TTL rg:lock:scheduler
```
A stale lock with no TTL indicates clock/Redis issues; a normal lock has TTL ≤ 55 s.

**Recover:**
1. Restart beat: `docker compose restart scheduler`.
2. If the lock is wedged, wait for TTL expiry; deleting it manually is a last
   resort and may allow a second scheduler to overlap briefly.
3. Confirm a manual tick: `docker compose exec api python -c "from app.workers.tasks.scheduler import enqueue_due_monitors; print(enqueue_due_monitors())"`.

**Verify:** `rg_scheduler_last_success_timestamp_seconds` advances; scheduled runs
appear; monitors' `last_checked_at` updates.

**Escalate:** SEV1 if monitoring is effectively blind for production.

---

## 5. Database unavailable

**Detect:** `/ready` returns 503 with `database: error`; API 500s;
`psycopg` connection errors in logs; managed provider incident.

**Contain:** Stop writes that cannot be retried safely (pause scheduler and
workers) to avoid a thundering herd. Do **not** point the app at a new empty
database.

**Investigate:** Check provider status, connection limits (`pg_stat_activity`),
long-running transactions, disk space, and failover state. Confirm whether the
primary or a replica is affected.

**Recover:** Fail over to the managed standby or restore per
[BACKUP-RESTORE.md](BACKUP-RESTORE.md). Run `alembic current` before resuming.

**Verify:** `/ready` is 200; run counts are continuous; no duplicate runs were
created during the outage (check `trigger` and timestamps).

**Escalate:** SEV1. Data loss is always SEV1 and requires an incident review.

---

## 6. Migration failed

**Detect:** Deploy stalls at `alembic upgrade head`; API fails readiness;
migration logs show a failed DDL statement.

**Contain:** Do not start the new API version. Keep the old version serving if
the schema change is backward compatible. Never "fix forward" with a destructive
statement on production without a backup.

**Investigate:** Read the migration and `alembic current`/`alembic history`.
Check for locks (`pg_locks`) and long transactions. Determine whether the failed
migration partially applied DDL.

**Recover:**
1. If the migration is transactional and rolled back, fix the migration or roll
   back the release.
2. If partially applied, follow the expand/contract plan for that migration;
   restore from backup only as a last resort.
3. `alembic downgrade -1` only when the migration has a tested downgrade and the
   previous code does not depend on the new schema.

**Verify:** `alembic current` matches the release; smoke run passes; data counts
match expectations.

**Escalate:** SEV2, SEV1 if production writes are blocked or data is at risk.

---

## 7. Notification provider unavailable

**Detect:** `NotificationFailures` alert; `NotificationAttempt.status="failed"`
spikes; webhook receiver errors/timeouts.

**Contain:** Nothing to contain in-app; incidents still open and are visible in
the dashboard. Do not disable notifications globally unless the provider is
causing retry storms.

**Investigate:** Inspect `NotificationAttempt.error`, provider status page, DNS,
webhook URL validity, and response codes. Check whether failures are one channel
or all channels.

**Recover:** Fix credentials/URLs, or add a secondary channel. Failed deliveries
retry with exponential backoff + jitter up to `NOTIFICATION_MAX_ATTEMPTS`;
escalation rules retry on each scheduler sweep until delivery succeeds.
Re-notify an incident by transitioning it (ack/resolve).

**Verify:** A test incident reaches all enabled channels; failure rate returns
below 1%.

**Escalate:** SEV2 if production alerts are not delivered; SEV3 for a single
tenant's misconfigured webhook.

---

## 8. False-positive incident storm

**Detect:** Many incidents for the same target/monitor; repeated open/resolve
cycles; customer reports noise; run evidence shows transient timeouts or
expected redirects.

**Contain:** Acknowledge incidents to stop paging. Disable only the noisy monitor
or raise its interval; avoid deleting incidents (they are audit evidence).

**Investigate:** Compare target region, timeout settings, expected status list,
and deployment events. Check whether checks ran during a known maintenance
window or a provider incident.

**Recover:** Fix monitor configuration (timeouts, expected status/text, redirect
policy), add a maintenance window/suppression if available, or adjust
consecutive-failure policy in code if the product lacks it.

**Verify:** 24 hours without recurrence; incident history shows a single
root-cause incident rather than many duplicates.

**Escalate:** SEV3, unless paging fatigue risks missing a real outage.

---

## 9. Suspected security breach

**Detect:** Unexpected admin activity, cross-tenant data exposure report,
anomalous API volume, SSRF spike, leaked credentials, or a provider alert.

**Contain:**
1. Revoke affected API keys and sessions (`api_keys` revoke, rotate
   `JWT_SECRET` to invalidate access tokens).
2. Disable the affected user/workspace if abuse is confirmed.
3. Block offending source IPs at the edge; keep `/metrics` and admin endpoints
   private.
4. Preserve logs and audit records; do not edit or delete them.

**Investigate:** Use `audit_logs`, structured API logs (`request_id`), blocked-URL
metrics, and storage access logs. Establish scope: which tenants, artifacts,
and credentials. Assume artifact URLs may have leaked; they expire after
`ARTIFACT_URL_TTL_SECONDS`.

**Recover:** Rotate secrets (JWT, webhook signing, S3 keys, DB password), patch
the vulnerability, redeploy, and force re-authentication. Notify affected
customers per policy/legal guidance.

**Verify:** No further anomalous requests; keys rotated; audit trail intact;
regression test added for the exploited path.

**Escalate:** SEV1 immediately; involve the security owner and legal/compliance.

---

## 10. Credentials compromised

**Detect:** Secret scanner finding, secret in a log/Slack/repo, provider alert,
or unexpected usage.

**Contain:** Revoke the credential at the source first, then update the
deployment secret store. Do not paste the secret into tickets or chat.

**Investigate:** Determine exposure window, systems that used it, and whether it
granted read or write access. Check audit logs and provider access logs.

**Recover:** Rotate all related credentials (database, S3, JWT, webhook, AI
provider). Deploy with the new values. Invalidate sessions if JWT signing was
exposed.

**Verify:** `python -m app.services.secret_scanner` returns no findings; the old
credential fails; no unauthorized activity after rotation.

**Escalate:** SEV1 when production or customer data may be affected.

---

## 11. Storage exhausted

**Detect:** `/ready` database disk alerts, artifact upload failures
(`rg_artifact_uploads_total{status="failure"}`), `ENOSPC` in logs, S3 quota or
bucket policy errors.

**Contain:** Stop non-essential artifact capture (temporarily set
`capture_screenshot=false` on noisy browser monitors) and pause large exports.
Do not delete the database volume.

**Investigate:** Identify the largest consumers: database tables/indexes, S3
prefix `artifacts/`, logs, or Playwright temp files. Check retention policy
execution and orphaned artifacts.

**Recover:** Expand storage, apply lifecycle rules, or delete artifacts past
retention. Re-run the sweeper to clear temp state. If the database is full,
`VACUUM`/index maintenance may be required.

**Verify:** Uploads succeed; disk usage below 80%; retention job runs; no new
`ENOSPC` errors.

**Escalate:** SEV2; SEV1 if the database cannot write.

---

## 12. Cost spike

**Detect:** Provider budget alert, daily spend > 2× baseline, unexpected egress,
AI token spike, or artifact growth.

**Contain:** Apply per-tenant quotas and lower `MAX_ACTIVE_RUNS_PER_WORKSPACE`;
disable unusually expensive monitors; set AI spending limits if enabled.

**Investigate:** Break down by driver (compute, storage, egress, notifications,
AI) using the model in [COST-VALIDATION.md](COST-VALIDATION.md). Correlate with
run volume, artifact size, and retention changes.

**Recover:** Right-size workers, enforce lifecycle rules, reduce retention,
batch notifications, and fix any runaway loop (e.g., a monitor enqueuing every
tick due to a scheduler bug).

**Verify:** Spend returns to baseline for 24–48 hours; quotas fire as intended;
no customer-visible failures.

**Escalate:** SEV2 if spend threatens the monthly budget; SEV3 for a slow drift.

---

## 13. Deployment regression

**Detect:** Post-deploy error/latency alert, failing smoke run, or a deployment
marked `failed` by Release Guardian itself (dogfooding).

**Contain:** Stop the rollout and, if the previous version is healthy, roll back
the image tag. Keep the database backward compatible.

**Investigate:** Compare error rate and latency by route before/after; inspect
the release diff, migrations, and feature flags. Check whether the regression is
in Release Guardian or the monitored target.

**Recover:**
1. `docker compose up -d --no-deps api worker scheduler` with the previous image
   tag (or platform rollback).
2. Run `alembic current`; downgrade only with a tested migration.
3. Re-run the smoke suite.

**Verify:** SLOs return to baseline; a deployment record for the fix is created;
the rollback is recorded in the incident timeline.

**Escalate:** SEV1 if customer monitoring is degraded; SEV2 for internal-only
regressions.

---

## 14. Backup restoration

**Detect:** Data loss/corruption, failed migration, provider incident, or a
scheduled drill.

**Contain:** Stop writes (pause scheduler/workers). Preserve the current database
before restoring, even if it is corrupt.

**Investigate:** Choose the recovery point (RPO ≤ 15 min). Confirm the backup's
timestamp, checksum, and Alembic revision. Identify dependent systems (Redis is
disposable; artifacts are in S3).

**Recover:** Follow [BACKUP-RESTORE.md](BACKUP-RESTORE.md). Restore into a new
database, validate, then switch the application connection string.

**Verify:** Row counts and `alembic_version` match the chosen point; `/ready` is
200; a smoke run completes; audit logs are intact.

**Escalate:** SEV1. Record actual RPO/RTO and update this runbook if the drill
reveals drift.
