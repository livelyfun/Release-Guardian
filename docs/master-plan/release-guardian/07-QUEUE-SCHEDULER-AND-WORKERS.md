# 07 — QUEUE, SCHEDULER, AND WORKERS

**Status:** Planning-only | **Date:** 2026-10-19

## Queue & Scheduler

- **Broker:** Redis (managed). Preferred **Celery + Redis**. Validate broker semantics (visibility timeout, pub/sub, locks) per provider. RQ viable; Temporal deferred.
- **Scheduler:** Celery Beat with advisory locks (prevent multiple schedulers); also support cron-style with lease. Missed schedules tracked, not double-executed.
- **Prioritization:** Deployment-event jobs higher priority than routine scheduled checks; per-tenant caps prevent starvation.
- **Backpressure:** Queue depth alerts, max concurrency per workspace/project/type, age-based alerts.
- **Idempotency:** Job keys (workspace+target+type+cron/hash) prevent duplicate enqueues where appropriate.

## Worker Model

- **Separation:** Browser workers isolated from API; different container pool, resource profiles (HTTP checks lighter; browser journeys/Lighthouse heavier).
- **Execution model:** Lease-based (visibility timeout), heartbeat, prefetch controlled, at-most-once + dedup + idempotent handling. 
- **Lifecycle:** SIGTERM → stop accepting new leases → drain in-flight (grace period) → SIGKILL if unresponsive → cleanup temp/artifacts dirs. 
- **Timeouts:** Per job (max), per step (browser actions), navigation, network idle, script execution; hard caps.
- **Retries:** Exponential backoff + jitter; retry only safe operations; max attempts; classify retryable vs non-retryable (e.g. permanent config error). DLQ for exhausted retries.
- **Cleanup:** Browser processes closed, ephemeral FS cleaned, temp files removed, orphaned browsers terminated on startup.

## Browser Automation

- **Test definition format:** Versioned JSON (or YAML in UI, stored as JSONB). Fields: version, name, steps[], assertions[], timeouts, tags, variables, credentials_ref (encrypted), options. Schema validated.
- **Supported actions (minimum):** navigate(url), click(locator), type(locator,text), wait_for(locator/state), wait_for_timeout(ms), check/uncheck, select_option, hover, press_key, screenshot(step), assert_* 
- **Assertions:** url_contains, text_contains, element_visible, element_count, status_code (if HTTP), console_errors (none/threshold), network_failures (none/threshold), custom expressions (deterministic only).
- **Execution states:** pending → leasing → initializing (browser launch) → running (steps) → capturing evidence → completed/failed/cancelled/inconclusive.
- **Evidence capture:** screenshots (step-level), traces (Playwright trace), HAR (network), console logs, network requests summary, page errors, step timing; redact PII.
- **Timeouts:** global job timeout, action timeout, navigation timeout, assertion timeout; configurable per check/test.
- **Retry policies:** Auto-retry only idempotent/safe checks; browser journeys generally not blindly retried unless explicit safe mode; use consecutive-failure policy.
- **Test credentials:** Stored encrypted, referenced by `credentials_ref`; never written to logs/artifacts; scoped to workspace/project/env; rotation supported.
- **Test-data cleanup:** Pre/post hooks (deterministic), cleanup best-effort on success/failure; track side-effects; avoid leaving test data.
- **Resource isolation:** Ephemeral browser container (non-root), read-only FS, tmpfs for artifacts dir, no host network where unsafe, CPU/mem caps, process limits, seccomp/AppArmor (platform-dependent). Network egress controlled by SSRF policy.

## Concurrency

- Concurrency limits by queue/type/workspace; scale workers horizontally by queue depth/age. Advisory locks for scheduler. Avoid DB connection pool exhaustion.
