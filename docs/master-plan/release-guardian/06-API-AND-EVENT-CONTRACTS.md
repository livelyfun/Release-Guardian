# 06 — API AND EVENT CONTRACTS

**Status:** Planning-only | **Date:** 2026-10-19

## API Design Principles

- Versioned REST: `/api/v1/...`
- Auth: bearer tokens (session or scoped API keys). Server-side authZ (resource/workspace scoped) on every request.
- Content: JSON (application/json). Validation via Pydantic.
- Pagination: cursor or limit/offset; include total/links.
- Idempotency: `Idempotency-Key` header for mutating requests (create/enqueue).
- Rate limits: per workspace/user/key (Redis-based), return `429` with `Retry-After`.
- Errors: standardized shape `{ "error": { "code": "...", "message": "...", "details": {...}, "request_id": "..." } }`

## Principal REST Operations (High-Level)

| Resource | Methods | AuthZ | Notes |
|---|---|---|---|
| `/workspaces` | GET, POST | authenticated | list/create |
| `/workspaces/{id}` | GET/PATCH/DELETE | owner/admin | tenant boundaries |
| `/projects` | CRUD | workspace member | tenant scoped |
| `/environments` | CRUD | workspace member | |
| `/check-configs` | CRUD | workspace member | schedule_cron |
| `/test-definitions` | GET/POST | workspace member | versioned (POST increments version) |
| `/test-definitions/{id}/versions` | GET | workspace member | |
| `/deployments` | GET/POST | workspace member | ingestion via webhook or manual |
| `/deployments/{id}/comparison` | GET | workspace member | compares checks with the previous passing deployment |
| `/monitors/{id}/regression-suppression` | GET/POST/DELETE | admin for writes | time-boxed suppression of performance-regression incidents |
| `/audit-runs` | POST/GET/GET/{id} | workspace member | group executions |
| `/test-runs` | GET/GET/{id} | workspace member | includes job_executions |
| `/job-executions` | GET/GET/{id} | workspace member | status, attempts, result_summary |
| `/job-executions/{id}/steps` | GET | workspace member | step timeline |
| `/workspaces/{id}/artifacts/signed-url?artifact_key=` | GET | workspace member | short-lived signed URL; verifies artifact ownership |
| `/baselines` | GET/PATCH | workspace member | N-samples, rotation |
| `/incidents` | GET/PATCH/POST | workspace member | lifecycle, ack/resolve |
| `/incidents/{id}/events` | GET | workspace member | timeline (append-only) |
| `/notification-channels` | CRUD | admin | config encrypted |
| `/integrations` | CRUD | admin | GitHub (least privilege) |
| `/api-credentials` | POST/GET/DELETE | admin | scoped, revocable, hash only |
| `/audit-logs` | GET | admin/owner (read audit) | append-only |
| `/health` `/ready` | GET | public/internal | liveness/readiness |

## Webhooks (Inbound)

- **GitHub:** verify `X-Hub-Signature-256` (HMAC-SHA256), validate payload, event type filter, idempotency by delivery GUID, reject replay outside window. Tenant mapping by repo/org.
- **Outgoing (platform webhooks):** signed (HMAC-SHA256 of body+timestamp), include `webhook-id`, `webhook-timestamp`, `webhook-signature`, idempotent delivery, retries with backoff.

## Event Contracts (Internal)

| Event | Publisher | Consumers | Notes |
|---|---|---|---|
| `job.queued` | API/Scheduler | Workers | job_id, workspace_id, project_id, type, version |
| `job.leased` | Worker | Observability | lease_owner, expires_at |
| `job.started` | Worker | Metrics/logs | attempt |
| `job.completed` | Worker | Control plane/notifications | result_summary (non-PII), duration |
| `job.failed` | Worker | DLQ/alerts | error_json (redacted) |
| `run.completed` | Control plane | Baselines/incidents/notifications | status, pass/fail, summary |
| `deployment.received` | API (webhook) | Scheduler | correlate |
| `incident.created/updated/resolved` | Control plane | Notifications | dedup key |
| `artifact.created` | Worker | Storage | references only |

## Versioning & Idempotency

- API version in path. Backward-compatible where feasible; deprecate with notice.
- Job payload versioning (`payload_version`); workers must handle or reject gracefully.
- `Idempotency-Key` prevents duplicate enqueues; store by key+workspace+resource.
- Webhook delivery idempotency by provider delivery ID + event type.
