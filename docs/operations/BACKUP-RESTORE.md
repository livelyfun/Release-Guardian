# Backup, Restore, and Rollback

**Status:** procedure + local drill script complete; staging/production drill
evidence outstanding.
**Last updated:** 2026-10-20

## Policy

| Environment | Backup | Retention | RPO | RTO |
|---|---|---|---|---|
| Local | None (disposable) | n/a | n/a | n/a |
| Staging | Daily logical dump + provider snapshots | 14 days | 24 h | 4 h |
| Production | Managed PITR + daily snapshot | PITR 7 days, daily 30 days, monthly 12 months | ≤ 15 min | ≤ 60 min |

**System of record:** PostgreSQL. Redis is a queue and may be rebuilt. S3
artifacts are stored in provider-durable storage with versioning; they are
regenerable by re-running checks.

Backups must be encrypted at rest and in transit, access-controlled, and stored
in a different region/account from the primary where the provider allows it.

## What is not backed up

- Individual browser sessions or in-flight worker state.
- Redis contents beyond AOF (queue loss is recovered by the stale-run sweeper).
- Local SQLite development databases.

## Backup commands

### Managed Postgres (production/staging)

Use the provider's PITR/snapshot feature; do not shell-dump production as the
only mechanism. Record the backup identifier and timestamp in the evidence log.

### Compose Postgres (local/staging drill)

```bash
mkdir -p /tmp/opencode/rg-backups
docker compose exec -T postgres \
  pg_dump -U release_guardian -d release_guardian --format=custom --no-owner \
  > /tmp/opencode/rg-backups/release_guardian-$(date -u +%Y%m%dT%H%M%SZ).dump
```

## Restore drill

The drill dumps the live database, restores into a **scratch** database,
compares row counts and the Alembic revision, then drops the scratch database.

```bash
scripts/backup_restore_drill.sh
# or
make drill-backup
```

Expected output:

```
[2/6] dumping release_guardian -> /tmp/opencode/rg-backups/release_guardian-....dump
[4/6] restoring dump into release_guardian_restore_drill
  ok users: 42
  ok workspaces: 7
  ok projects: 9
  ok environments: 12
  ok monitors: 31
  ok runs: 1840
  ok step_results: 2911
  ok incidents: 6
  ok alembic_version: <revision>
RESULT: PASSED
```

The drill never touches the source database and drops the scratch database on
exit unless `KEEP_DRILL_DB=1` is set.

## Actual restore procedure

1. **Declare an incident and stop writes.** Pause the scheduler and workers so
   the restored database is not immediately mutated.
2. **Preserve the current database**, even if corrupt:
   `pg_dump ... > before-restore.dump` (or take a provider snapshot).
3. **Choose the recovery point** (timestamp within RPO). Confirm the backup's
   timestamp and Alembic revision.
4. **Restore into a new database**, not over the live one:
   - Managed: restore/PITR to a new branch or instance.
   - Dump: `createdb rg_restore`, then
     `pg_restore -U <user> -d rg_restore --no-owner --exit-on-error < dump`.
5. **Validate before cutover:**
   ```bash
   psql "$RESTORE_URL" -c "SELECT version_num FROM alembic_version;"
   psql "$RESTORE_URL" -c "SELECT count(*) FROM runs;"
   psql "$RESTORE_URL" -c "SELECT count(*) FROM users;"
   ```
   Run the application against the restored database with `alembic upgrade head`
   (should be a no-op) and a smoke run.
6. **Cut over** by updating `DATABASE_URL`, then restart API/worker/scheduler.
7. **Verify** `/ready`, a manual run, and incident history continuity.
8. **Re-enable** scheduling and workers; monitor `rg_queue_depth` and error rate.

## Rollback drill

Rollback is image + schema, not a database restore, unless the schema change is
destructive.

### Preconditions

- Migrations are expand/contract and backward compatible for one release.
- The previous image tag/digest is recorded.
- The migration has a tested `downgrade()` if it is reverted.

### Steps

1. Freeze deploys and note the failing revision.
2. Deploy the previous API, worker, and scheduler image/commit. For Compose:
   ```bash
   git checkout <previous-sha>
   docker compose up -d --build api worker scheduler
   ```
   For a registry-based platform, redeploy the previous digest.
3. Check `alembic current`. If the previous code is compatible with the current
   schema (expand/contract), **do not downgrade**.
4. If a downgrade is required, run `alembic downgrade -1` only after a verified
   backup, and confirm no new columns/tables are in use.
5. Run the smoke suite and a manual monitor run.
6. Record start/end time, image digests, migration revision, and verification
   result.

### Pass criteria

- Rollback completes within 15 minutes.
- `/ready` is 200 and smoke runs pass.
- No data loss beyond the announced change window.
- Migration revision and image version match the intended release.

## Evidence log

Fill in for every drill. Attach the drill output and provider backup ID.

| Date | Environment | Drill | Backup/Revision | Result | RPO/RTO actual | Operator |
|---|---|---|---|---|---|---|
| _pending_ | staging | backup/restore | | | | |
| _pending_ | staging | rollback | | | | |
| _pending_ | production | backup/restore | | | | |

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `pg_restore: extension ... does not exist` | Managed provider requires extension creation first | Create extensions before restore; coordinate with provider |
| Row-count mismatch | Dump taken while writes were in flight | Stop writes, re-dump, re-run drill |
| `alembic_version` mismatch | Restored an older dump | Run `alembic upgrade head` against the restored DB and re-verify |
| Restore exceeds RTO | Dump size/IOPS or network | Use provider snapshot/PITR; increase parallelism; document actual time |
| Scratch DB creation fails | Active connections / permissions | Terminate scratch connections; verify role privileges |
