# 13 — COST AND CAPACITY MODEL

**Status:** Planning-only | **Date:** 2026-10-19

Transparent model of resource use. Figures below are **drivers and assumptions**, not verified pricing (see [17-SOURCE-REGISTER.md](17-SOURCE-REGISTER.md)).

## Principal Cost Drivers

| Driver | Notes |
|---|---|
| Hosting (control plane) | API + scheduler containers |
| Browser workers | heaviest cost; one-job-per-container isolation |
| Lighthouse audits | CPU/memory spikes |
| Database compute + storage | Neon or equivalent; growth with history/artifacts |
| Queue operations | Redis-managed |
| Artifact storage | screenshots/traces grow fastest |
| Network egress | artifact download, cross-region checks |
| Email / messaging | notification volume |
| Logs and traces | retention-sensitive |
| External monitoring regions | multiply check cost |
| AI token consumption | only if enabled; metered |
| Billing provider | if usage metering/billing enabled |

## Capacity Assumptions (to validate)

- Concurrent audits per worker pool size.
- Scheduler processing time vs. number of due checks.
- Database connection limits (pooling) vs. concurrency.
- Browser memory/CPU per concurrent journey.
- Artifact storage growth rate per project/month.

## Controls

- Per-tenant quotas and rate limits.
- Concurrency caps per workspace/project/job type.
- Artifact retention and lifecycle policies.
- AI spending limits.
- Cost-spike alerting (see [11-OBSERVABILITY-AND-OPERATIONS.md](11-OBSERVABILITY-AND-OPERATIONS.md)).

## Scaling Path

- Scale horizontally: stateless API, worker pools by job class (HTTP vs. browser vs. Lighthouse).
- Separate heavier workload pools before scaling database.
- Partition/read-replica only when projected workload justifies (do not overengineer early).

## Validation Required

Owner must verify current provider pricing, regions, and limits before financial commitments.
