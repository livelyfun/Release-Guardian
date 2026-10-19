# 10 — DEPLOYMENT AND CI/CD

**Status:** Planning-only | **Date:** 2026-10-19

## Environments

| Env | Purpose | Data | Hosting |
|---|---|---|---|
| Local | Development | Docker Compose (PG, Redis, MinIO optional) | Developer |
| Preview | Per-PR (frontend) + ephemeral API/workers | Branch DB (Neon branch), isolated storage prefix | Vercel + managed |
| Staging | Pre-prod validation | Production-like, seeded | Managed hybrid |
| Production | Live | Backups/PITR, strict authZ/SSRF | Managed hybrid |

## CI/CD Pipeline

1. Lint/format/typecheck
2. Unit + integration tests (containerized services)
3. Security gates (SSRF matrix, tenant isolation, secret redaction, webhook verification)
4. Build images (API, worker, scheduler); SBOM + dependency scan
5. Push images; deploy to staging; run migrations (forward-compatible)
6. E2E smoke on staging (fixture target)
7. Manual/auto approval → production rollout
8. Post-deploy verification (Release Guardian verifying itself — dogfooding)

## Deployment Gates

- Migrations backward-compatible; no destructive changes without expand/contract.
- Health/readiness checks pass before traffic shift.
- Critical tests (authZ, SSRF, queue) green.
- Rollback plan verified (image tag + migration rollback strategy).

## Rollback Procedures

- **App:** Re-deploy previous known-good image tag (immutable). 
- **DB:** Prefer backward-compatible migrations so no DB rollback needed; otherwise restore/repair via expand-contract.
- **Queue:** Drain/replay DLQ; ensure payload version compatibility.
- **Feature flags:** Disable new risky features quickly (e.g. browser journeys) without redeploy.

## Local Reproducibility (Not Authorized Yet)

- Compose file with PG/Redis/MinIO + API + worker + scheduler for parity.
- Seed scripts for demo project/target.
- Fixture web server for deterministic checks (safe, loopback-allowed only in test mode).
