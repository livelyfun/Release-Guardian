# 03 — TECHNOLOGY DECISIONS

**Status:** Planning-only | **Date:** 2026-10-19

## Weighted Architecture Decision Matrix

**Criteria & weights (justified):**

| Criterion | Weight | Rationale |
|---|---|---|
| Reliability & failure recovery | 20% | Core to "release guardian" (resilient execution, retries, recovery) |
| Security & browser isolation | 20% | SSRF + untrusted browser execution = highest risk |
| Operational complexity | 15% | Maintainability, time-to-value, sustainable ops |
| Scalability & concurrency | 15% | Bursty deploy events + browser-heavy workloads |
| Cost & predictability | 10% | Prevent uncontrolled spend (workers/artifacts) |
| Developer productivity | 10% | Local reproducibility, DX |
| Portability & exit costs | 5% | Avoid irreversible lock-in |
| Observability & maintainability | 5% | Evidence-first, debuggability |

**Scoring (1–10, higher better):**

| Option | Rel(20) | Sec(20) | Ops(15) | Scal(15) | Cost(10) | Dev(10) | Port(5) | Obs(5) | Weighted (out of 100) | Confidence (1–10) |
|---|---|---|---|---|---|---|---|---|---|---|
| A. Managed hybrid (Vercel + managed containers + Neon + Redis + S3-compatible/R2) | 9×20=180 | 9×20=180 | 9×15=135 | 9×15=135 | 8×10=80 | 9×10=90 | 6×5=30 | 9×5=45 | **875** | 9 |
| B. Self-hosted containers (Docker Compose/VPS + self-managed PG/Redis/MinIO) | 7×20=140 | 8×20=160 | 5×15=75 | 7×15=105 | 9×10=90 | 6×10=60 | 10×5=50 | 7×5=35 | **715** | 8 |
| C. Cloud-native/K8s | 9×20=180 | 9×20=180 | 4×15=60 | 10×15=150 | 5×10=50 | 5×10=50 | 7×5=35 | 9×5=45 | **750** | 7 |

**Rationale:** A balances security/isolation + operational simplicity + predictable scaling. C scales but adds premature complexity (low ops score). B low ops/high exit cost tradeoff.

**Recommendation:** **Option A (Managed hybrid).** Confidence 9. Assumptions documented; provider-dependent details remain unresolved until selected.

## Finalized Proposed Stack

| Layer | Technology (proposed) | Notes/Uncertainties |
|---|---|---|
| Frontend | Next.js (App Router, TypeScript) | Vercel hosting. SSR/typed client; no hard provider lock-in for app code. |
| API (Control Plane) | FastAPI (Python 3.11+) + Pydantic v2 | Modular monolith; OpenAPI; tenant scoping enforced server-side. |
| Workers | Python (Celery or RQ). Playwright + Lighthouse | Browser isolation in separate containers. **Auth boundary:** API owns authZ; workers receive job-scoped context (no tenant escalation). |
| Queue/Scheduler | **Celery + Redis** (preferred) vs RQ. Beat for scheduler. | Managed Redis compatibility varies (Upstash/Render/Redis Cloud) — validate broker semantics (visibility timeout, pub/sub, locks) before final provider choice. Temporal deferred unless workflow complexity increases. |
| DB | PostgreSQL 15+ (Neon recommended start) | PITR, branching useful for previews; RLS as defense-in-depth. Provider-dependent connection limits/IOPS unresolved. |
| Object Storage | S3-compatible (Cloudflare R2 preferred) | Zero/low egress, lifecycle/retention, signed URLs scoped to tenant/project. |
| Auth | Better Auth (self-hostable) or Clerk (managed) | Prefer self-hostable to avoid data lock-in; OIDC extensible for future SSO. Decision open (see [16-OPEN-DECISIONS.md](16-OPEN-DECISIONS.md)). |
| Deployment Topology | API/scheduler/workers as containers; frontend Vercel | Workers isolated pool (separate CPU/mem/time limits). |
| Observability | JSON logs, metrics (Prometheus-style), OTel (optional), error tracking | Correlation IDs (job/run/attempt/step). PII redaction. |

**Worker lifecycle:** Pull jobs by lease, heartbeat, idempotent processing, timeouts, cancellation-safe where possible, graceful shutdown (SIGTERM → drain → SIGKILL), per-job cleanup, replace after corruption/timeout abuse. Browser processes killed on completion/failure.

**Remaining provider-dependent uncertainties:** Redis broker features (exact visibility timeouts/clustering), Neon connection pooling/branching behavior, R2 lifecycle semantics, worker cold-start/exec time limits per platform — document as assumptions until verified.
