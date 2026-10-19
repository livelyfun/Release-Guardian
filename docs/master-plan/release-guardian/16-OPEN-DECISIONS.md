# 16 — OPEN DECISIONS

**Project:** Release Guardian
**Date:** 2026-10-19

Each item requires an owner decision. Recommended options are listed first. Until a decision is
recorded, the recommendation is treated as a working assumption, not a commitment.

## D1 — Browser execution isolation model

- **Question:** How are untrusted websites executed safely?
- **Options:** (a) Dedicated Playwright worker containers with egress firewall and per-job limits;
  (b) microVM isolation (e.g., Firecracker) per job; (c) third-party browser execution service.
- **Recommendation:** (a) for the first production deployment; revisit (b) at scale or on
  enterprise demand.
- **Consequence:** (a) is cheaper and simpler but shares a kernel; (b) offers stronger isolation
  at higher operational cost.

## D2 — Queue/workflow engine

- **Question:** Celery/Redis or a durable workflow engine?
- **Options:** (a) Celery + Redis (current); (b) Temporal; (c) another broker.
- **Recommendation:** Stay with Celery until retries, cancellation, or multi-step workflows make
  durability the dominant concern.
- **Consequence:** Celery requires custom idempotency and dead-letter handling; Temporal adds
  operational components.

## D3 — Initial hosting

- **Question:** Where do API, workers, scheduler, Postgres, and Redis run?
- **Options:** (a) Managed hybrid (Vercel + container host + Neon + managed Redis); (b) single VPS
  with Docker Compose; (c) cloud-native orchestration.
- **Recommendation:** (a) for launch; (b) for a cost-sensitive private beta.
- **Consequence:** Managed services reduce operations but add vendor dependencies and egress cost.

## D4 — Object storage for evidence

- **Question:** Where are screenshots, traces, and reports stored?
- **Options:** (a) S3-compatible storage (Neon/AWS/R2); (b) database blobs; (c) local volume.
- **Recommendation:** (a), with signed URLs and retention policy.
- **Consequence:** Requires credential management and lifecycle rules; (b) is simpler but costly
  and poor for large artifacts.

## D5 — Authentication for the public API

- **Question:** API keys only, or OAuth/app installations too?
- **Options:** (a) Workspace API keys with scopes (current model); (b) GitHub App tokens;
  (c) OAuth 2.0 client credentials.
- **Recommendation:** (a) first; add (b) for repository/deployment integrations.
- **Consequence:** Keys require secure storage, rotation, and revocation UX.

## D6 — AI assistance timing

- **Question:** Ship AI diagnosis in the first release?
- **Options:** (a) Defer until evidence model and integrations are mature; (b) ship read-only
  summarization early; (c) defer indefinitely.
- **Recommendation:** (a).
- **Consequence:** Keeps the deterministic core trustworthy and avoids premature data-sharing
  commitments.

## D7 — Billing provider and pricing model

- **Question:** Which payment provider and plan structure?
- **Options:** (a) Stripe subscriptions with usage add-ons; (b) invoice-based enterprise only;
  (c) no billing until post-beta.
- **Recommendation:** (c) during beta, then (a).
- **Consequence:** Usage metering must be correct before charging; provider fees and tax handling
  vary by country.

## D8 — Data retention defaults

- **Question:** How long are runs, artifacts, and audit logs retained per plan?
- **Options:** (a) 30/90/365-day tiers; (b) unlimited with storage add-ons; (c) customer-configurable.
- **Recommendation:** (a), with configurable overrides for enterprise.
- **Consequence:** Retention affects cost, deletion semantics, and compliance obligations.
