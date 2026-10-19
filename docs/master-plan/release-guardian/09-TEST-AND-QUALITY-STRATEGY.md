# 09 — TEST AND QUALITY STRATEGY

**Status:** Planning-only | **Date:** 2026-10-19

## Test Pyramid

- **Unit:** Pure logic (validation, SSRF checks, scheduling math, dedup keys, state machines).
- **Integration:** API + DB + Redis + object storage (sandboxed), queue semantics, RLS/authZ, migrations.
- **Contract:** OpenAPI schema validation against implementation; webhook signature/verification.
- **E2E Smoke:** Deploy a demo target (fixture server) → run journey → assert evidence.
- **Security:** SSRF matrix (loopback/private/redirects/rebind/IPv6/metadata/WebSocket/subresource), tenant isolation (cross-tenant negative), secret redaction, webhook spoofing.
- **Resilience:** Worker crash/restart, queue backlog/backpressure, DLQ, scheduler duplicate prevention, DB failover, storage outage, browser process kill.
- **Performance/Load:** Queue throughput, worker scaling, API latency under load; Lighthouse baseline stability.

## Quality Gates (CI)

| Gate | Check | Required |
|---|---|---|
| Lint/Format/Type | ruff/flake8/mypy; ESLint/TS | Yes |
| Unit/Integration | Core logic, authZ, queue, migrations | Yes |
| Tenant Isolation | Cross-tenant negative tests | Yes |
| SSRF Hardening | Loopback/private/redirect/rebind/IPv6 | Yes |
| Contract/Webhook | OpenAPI + signature tests | Yes |
| E2E Smoke | Critical journey in staging | Yes |
| Migrations | Versioned, backward-compatible, rollback plan | Yes |
| Secrets/Redaction | No secrets in logs/artifacts tests | Yes |
| SBOM/SCA | Dependency scan (critical/high) | Yes (pre-release) |
| Load (periodic) | Queue/throughput targets | Yes (before scale milestones) |

## Flakiness Management

- Consecutive-failure policy (e.g. fail after N consecutive) to avoid false incidents.
- Baseline eligibility requires stable N samples (e.g. 20–30) with low variance.
- Distinguish environment noise (network) vs real regression (content) where possible.
- Track flaky rate per test; quarantine/flag flaky tests; do not blindly retry browser journeys.

## Definition of Done (per feature)

- AuthZ/tenant scoping verified
- Tests (unit/integration/security where applicable)
- Observability (logs/metrics/correlation IDs)
- Docs updated (contracts/data model)
- Runbook impact noted
