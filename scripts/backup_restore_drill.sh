#!/usr/bin/env bash
# PostgreSQL backup/restore drill for Release Guardian.
#
# Dumps the compose Postgres database with pg_dump, restores it into a scratch
# database, compares row counts for core tables, and drops the scratch database.
# A failed comparison exits non-zero so CI or an operator can gate a release.
#
# Usage:
#   scripts/backup_restore_drill.sh
#   COMPOSE_FILE=docker-compose.yml BACKUP_DIR=/var/backups/rg scripts/backup_restore_drill.sh
#
# Requirements: docker compose stack running (make up), pg_dump/pg_restore inside
# the postgres image (included in postgres:16-alpine).

set -euo pipefail
umask 077

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}
POSTGRES_SERVICE=${POSTGRES_SERVICE:-postgres}
POSTGRES_USER=${POSTGRES_USER:-release_guardian}
POSTGRES_DB=${POSTGRES_DB:-release_guardian}
DRILL_DB=${DRILL_DB:-release_guardian_restore_drill}
BACKUP_DIR=${BACKUP_DIR:-/tmp/opencode/rg-backups}
KEEP_DRILL_DB=${KEEP_DRILL_DB:-0}

# The drill database name is interpolated into SQL identifiers, so constrain it
# to a safe unquoted identifier before any statement is built.
if [[ ! "$DRILL_DB" =~ ^[A-Za-z_][A-Za-z0-9_]{0,62}$ ]]; then
  echo "DRILL_DB must be a valid unquoted PostgreSQL identifier" >&2
  exit 2
fi

TABLES=(users workspaces memberships projects environments monitors runs step_results incidents)

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_file="${BACKUP_DIR}/release_guardian-${timestamp}.dump"

mkdir -p "$BACKUP_DIR"

dc() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

cleanup() {
  if [[ "$KEEP_DRILL_DB" != "1" ]]; then
    dc exec -T "$POSTGRES_SERVICE" \
      psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
      -c "DROP DATABASE IF EXISTS ${DRILL_DB};" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[1/6] checking compose postgres service"
dc exec -T "$POSTGRES_SERVICE" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null

echo "[2/6] dumping ${POSTGRES_DB} -> ${backup_file}"
dc exec -T "$POSTGRES_SERVICE" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner \
  > "$backup_file"
test -s "$backup_file"

echo "[3/6] creating scratch database ${DRILL_DB}"
dc exec -T "$POSTGRES_SERVICE" \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${DRILL_DB};" \
  -c "CREATE DATABASE ${DRILL_DB};" >/dev/null

echo "[4/6] restoring dump into ${DRILL_DB}"
dc exec -T "$POSTGRES_SERVICE" \
  pg_restore -U "$POSTGRES_USER" -d "$DRILL_DB" --no-owner --exit-on-error \
  < "$backup_file"

echo "[5/6] comparing row counts"
failed=0
for table in "${TABLES[@]}"; do
  source_count=$(dc exec -T "$POSTGRES_SERVICE" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM ${table};" | tr -d '[:space:]')
  restored_count=$(dc exec -T "$POSTGRES_SERVICE" \
    psql -U "$POSTGRES_USER" -d "$DRILL_DB" -tAc "SELECT count(*) FROM ${table};" | tr -d '[:space:]')
  if [[ "$source_count" != "$restored_count" ]]; then
    echo "  MISMATCH ${table}: source=${source_count} restored=${restored_count}"
    failed=1
  else
    echo "  ok ${table}: ${source_count}"
  fi
done

source_revision=$(dc exec -T "$POSTGRES_SERVICE" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT version_num FROM alembic_version;" | tr -d '[:space:]')
restored_revision=$(dc exec -T "$POSTGRES_SERVICE" \
  psql -U "$POSTGRES_USER" -d "$DRILL_DB" -tAc "SELECT version_num FROM alembic_version;" | tr -d '[:space:]')
if [[ "$source_revision" != "$restored_revision" ]]; then
  echo "  MISMATCH alembic_version: source=${source_revision} restored=${restored_revision}"
  failed=1
else
  echo "  ok alembic_version: ${source_revision}"
fi

echo "[6/6] backup size: $(du -h "$backup_file" | cut -f1) (${backup_file})"

if [[ "$failed" -ne 0 ]]; then
  echo "RESULT: FAILED"
  exit 1
fi

echo "RESULT: PASSED"
