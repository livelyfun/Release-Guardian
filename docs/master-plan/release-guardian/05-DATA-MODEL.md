# 05 — DATA MODEL (Logical Schema + ERD)

**Status:** Planning-only | **Date:** 2026-10-19

## Core Principles

- **Tenant ownership:** Every tenant-scoped entity has `workspace_id` (FK to workspaces). Server-side authZ + RLS (defense-in-depth).
- **Soft deletes preferred** for audit/history where feasible; hard deletes follow documented lifecycle.
- **Immutability:** run/step/artifact references immutable after write; audit logs append-only.
- **IDs:** Prefer UUIDv7 or UUIDv4; job/execution identifiers stable.
- **Timestamps:** UTC, `created_at/updated_at` with timezone-aware types.
- **Versioning:** test_definitions versioned (`version`, `definition_hash`).

## Entity-Relationship (Conceptual)

```text
users (1:N) workspaces (1:N) memberships
workspaces (1:N) projects (1:N) environments
projects (1:N) monitored_targets (1:N) check_configs
projects (1:N) test_definitions (1:N) test_runs
environments (1:N) deployments (1:N) audit_runs
audit_runs/test_runs (1:N) job_executions (1:N) step_results
job_executions (1:N) artifacts
projects/environments (1:N) baselines, incidents (1:N) incident_events
workspaces (1:N) notification_channels (1:N) notification_attempts
workspaces (1:N) api_credentials, integrations, usage_records, subscriptions
workspaces (1:N) audit_log_entries
```

## Key Entities (Fields Summary)

| Entity | Key Fields | Constraints/Indexes | Notes |
|---|---|---|---|
| users | id (PK), email (unique), email_verified_at, password_hash (nullable), created_at, updated_at, last_login_at | idx_email, idx_created | Auth provider may externalize; store minimal profile |
| workspaces | id (PK), name, slug (unique), owner_id (FK users), created_at, updated_at, deleted_at | idx_slug, idx_owner | Tenant root |
| memberships | id (PK), workspace_id (FK), user_id (FK), role (enum: owner/admin/dev/viewer), created_at | (workspace_id,user_id) unique, idx_role | RBAC |
| projects | id (PK), workspace_id (FK), name, slug, created_at, updated_at, archived_at | (workspace_id,slug) unique, idx_workspace | Tenant-scoped |
| environments | id (PK), project_id (FK), workspace_id (FK), name, kind (prod/staging/preview/custom), url, created_at | (project_id,name) unique, idx_workspace, idx_project | Denormalize workspace_id for tenant scoping |
| monitored_targets | id (PK), project_id(FK), workspace_id(FK), url, created_at | idx_workspace, idx_project | HTTP/base targets |
| check_configs | id (PK), project_id(FK), workspace_id(FK), env_id(FK null), type (http/browser/lighthouse), schedule_cron, enabled, timeout_ms, retries, created_at | idx_workspace, idx_project, idx_enabled | Scheduling config |
| test_definitions | id (PK), project_id(FK), workspace_id(FK), name, version (int), definition_hash, definition_json (jsonb), created_at | (project_id,name,version) unique, idx_workspace, idx_hash | Versioned journey definitions |
| deployments | id (PK), project_id(FK), workspace_id(FK), env_id(FK), provider (github), ref/sha, deploy_id, deployed_at, payload_json(jsonb) | idx_workspace, idx_project, idx_env, idx_deploy_id, idx_deployed_at | Correlation key |
| audit_runs | id (PK), workspace_id(FK), project_id(FK), env_id(FK), triggered_by (enum), trigger_meta(jsonb), created_at | idx_workspace, idx_project, idx_env, idx_created | Grouping |
| test_runs | id (PK), audit_run_id(FK), test_definition_id(FK), workspace_id(FK), project_id(FK), env_id(FK), status(enum: pending/running/passed/failed/inconclusive/cancelled), started_at, finished_at, duration_ms | idx_workspace, idx_project, idx_env, idx_status, idx_started_at | Execution grouping |
| job_executions | id (PK), test_run_id(FK null), audit_run_id(FK null), workspace_id(FK), project_id(FK), type, payload_version, status(enum), attempt(int), lease_owner, lease_expires_at, worker_id, started_at, finished_at, duration_ms, result_summary(jsonb), error_json(jsonb) | idx_workspace, idx_status, idx_lease_expires, idx_started_at, idx_type | Idempotent; lease-based |
| step_results | id (PK), job_execution_id(FK), workspace_id(FK), seq(int), name, action, status, duration_ms, locator, assertion, evidence_refs(jsonb), console_errors(jsonb), network_failures(jsonb), created_at | idx_job_exec, idx_workspace, idx_seq | Immutable after write |
| artifacts | id (PK), job_execution_id(FK), workspace_id(FK), project_id(FK), kind (screenshot/trace/har/lighthouse/html/json), storage_key, sha256, size_bytes, content_type, created_at, expires_at | idx_workspace, idx_job_exec, idx_kind, idx_expires | References only; signed access |
| baselines | id (PK), workspace_id(FK), project_id(FK), env_id(FK), check_config_id(FK), test_definition_id(FK), metric_key, baseline_json(jsonb), samples_count, established_at, expires_at, created_at | idx_workspace, idx_project, idx_env, idx_metric | N-samples eligibility; rotation |
| incidents | id (PK), workspace_id(FK), project_id(FK), env_id(FK), severity(enum), status(enum), title, summary, dedup_key, first_seen_at, last_seen_at, acked_at, resolved_at, resolved_by, root_cause | idx_workspace, idx_project, idx_env, idx_status, idx_severity, idx_dedup_key, idx_last_seen | Deduplication key (project+env+check/test+failure_signature) |
| incident_events | id (PK), incident_id(FK), workspace_id(FK), event_type, actor, message, evidence_refs(jsonb), created_at | idx_incident, idx_workspace, idx_created | Timeline (append-only) |
| notification_channels | id (PK), workspace_id(FK), type, config_encrypted(jsonb), enabled, created_at, updated_at | idx_workspace, idx_enabled | Secrets encrypted at rest |
| notification_attempts | id (PK), channel_id(FK), workspace_id(FK), incident_id(FK), job_execution_id(FK), status, attempts(int), last_attempt_at, next_retry_at, error | idx_workspace, idx_status, idx_next_retry | Backoff+jitter, retry caps |
| integrations | id (PK), workspace_id(FK), provider, access_token_encrypted, refresh_token_encrypted, scopes, installed_at, revoked_at | idx_workspace, idx_provider | GitHub etc (least privilege) |
| api_credentials | id (PK), workspace_id(FK), name, key_id, key_hash, scopes, expires_at, last_used_at, revoked_at, created_at | idx_workspace, idx_key_id | Scoped/revocable; store hash only |
| audit_log_entries | id (PK), workspace_id(FK), actor_id(FK null), action, resource_type, resource_id, ip, user_agent, meta(jsonb), created_at | idx_workspace, idx_created, idx_action | Append-only |
| usage_records | id (PK), workspace_id(FK), period_start, period_end, metric, quantity, unit, meta(jsonb), created_at | idx_workspace, idx_period | Metering for future billing |
| subscriptions | id (PK), workspace_id(FK), provider, plan, status, current_period_start, current_period_end, cancel_at_period_end, created_at, updated_at | idx_workspace, idx_status | Isolated from core |

## Deletion Semantics & Retention

- **Workspaces/projects deletion:** Soft-delete first (archived/deleted_at). Hard-delete follows retention window + cascading rules with audit trail.
- **Runs/steps:** Retained per policy (e.g. 30d non-prod, 90d prod, configurable). Large tables may partition by `created_at` later.
- **Artifacts:** Lifecycle policy (auto-expire at `expires_at`), deleted from storage after DB reference removed; signed URLs short-lived.
- **Audit logs:** Append-only, longer retention (compliance-dependent) — do not hard-delete without policy.
- **PII:** Redact in logs/artifacts; credentials encrypted; hashes only for API keys.

## Migration Requirements

- Versioned migrations (e.g. Alembic). Forward/backward where feasible; backward-compatible for queue payloads.
- Tenant-scoping enforced in migrations/queries (RLS optional defense-in-depth).
- Index changes planned to avoid long locks; large backfills batched.
