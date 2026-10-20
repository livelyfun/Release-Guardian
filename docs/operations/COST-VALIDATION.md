# Cost Validation

**Status:** model and controls implemented; provider prices and production
volumes still need validation.
**Last updated:** 2026-10-20

## Principle

Cost is a product constraint, not an afterthought. This document separates
**drivers** (things the product controls) from **prices** (things the provider
controls). The model is reproducible; prices are inputs and must be verified
before financial commitments.

## Drivers

| Driver | Unit | Product controls |
|---|---|---|
| HTTP checks | executions/month | monitor intervals, retention, dedupe |
| Browser journeys | executions/month × seconds | journey length, concurrency caps, retries |
| Lighthouse audits | executions/month × seconds | audit frequency, worker isolation |
| Artifact storage | GB-month | screenshot/trace capture, retention, compression |
| Network egress | GB | signed-URL downloads, cross-region checks |
| Database | compute + storage | history retention, indexes, pooling |
| Redis | managed instance | queue depth, AOF, HA |
| Notifications | attempts | dedupe, channel count, escalation |
| Logs/traces | GB ingested | retention, sampling |
| AI tokens | calls × tokens | feature gating, spending limits |

## Reproducible model

```bash
python scripts/cost_model.py \
  --checks-per-month 200000 \
  --browser-share 0.20 \
  --lighthouse-share 0.05 \
  --output /tmp/opencode/cost-model.json
```

Example output (prices are illustrative placeholders; replace them):

```json
{
  "volume": {
    "http_checks": 150000,
    "browser_checks": 40000,
    "lighthouse_checks": 10000,
    "worker_hours": 708.3,
    "artifact_gb_retained": 47.7
  },
  "components_usd": {
    "worker_compute": 35.42,
    "artifact_storage": 1.10,
    "network_egress": 4.50,
    "notifications": 5.00,
    "database": 100.00,
    "redis": 30.00,
    "fixed_hosting": 150.00,
    "ai_tokens": 0.00
  },
  "total_month_usd": 326.02,
  "cost_per_check_usd": 0.00163
}
```

At this volume the marginal execution cost is small; the fixed control-plane
and database costs dominate. Re-run with real provider prices and measured
durations before setting prices or plan limits.

## Capacity math

Average monthly volume hides peaks. Use peak-to-average ratio from the load
test and expected schedule clustering.

```
required_workers ≈ peak_checks_per_minute
                 × share(kind)
                 × seconds_per_check(kind)
                 ÷ 60
```

For 200 000 checks/month, a 10× peak, 20% browser, 5% Lighthouse, and 45 s/60 s
durations:

| Kind | Peak/min | Seconds each | Worker-seconds/min | Concurrent workers |
|---|---|---|---|---|
| HTTP | 30.9 | 1 | 31 | 1 |
| Browser | 7.7 | 45 | 347 | 5.8 |
| Lighthouse | 1.9 | 60 | 116 | 1.9 |
| **Total** | | | **494** | **≈ 9** |

Add headroom for retries and rolling deploys (1.5–2×). Browser and Lighthouse
workers should be a separate pool from HTTP checks so a heavy audit cannot
starve availability checks.

Connection pooling: each worker holds a small number of DB connections; size
the pool to `workers × concurrency + API replicas`, below the provider limit.

## Artifact growth

```
steady_state_GB ≈ checks_per_month × (retention_days / 30) × KB_per_check ÷ 1,048,576
```

At 250 KB/check and 30-day retention, 200 000 checks/month ≈ **47.7 GB**.
Screenshots dominate; Lighthouse JSON is usually 300–600 KB and should be
stored only when `save_assets` is enabled. Capture is best-effort, so an outage
does not block checks.

## Controls in the implementation

| Control | Location |
|---|---|
| Per-monitor active-run ceiling | `MAX_ACTIVE_RUNS_PER_MONITOR` (`services/capacity.py`) |
| Per-workspace active-run ceiling | `MAX_ACTIVE_RUNS_PER_WORKSPACE` |
| Per-identity rate limits | `core/rate_limit.py` |
| Run/step/Celery time limits | `RUN_TIMEOUT_SECONDS`, `STEP_TIMEOUT_SECONDS`, `celery_app.py` |
| Scheduled checks skip when a run is active | `workers/tasks/scheduler.py` |
| Deployment fan-out skips active monitors | `services/runs.py` |
| Artifact capture opt-out per monitor | `config.capture_screenshot=false` |
| Artifact retention config | **Not automated yet** — bucket lifecycle rule required |
| AI spending limit | `AIConfiguration` model (enforcement pending) |

## Validation checklist

- [ ] Replace all unit prices with current provider quotes (region-specific).
- [ ] Measure real artifact size: `SELECT avg(size_bytes) FROM artifacts;`
- [ ] Measure run durations: `rg_run_duration_seconds` p50/p95 by kind.
- [ ] Confirm peak-to-average ratio from staging load test.
- [ ] Confirm worker density (concurrent browser checks per instance) without
      hitting CPU/memory limits or browser crashes.
- [ ] Set artifact lifecycle rules and verify deletion after retention.
- [ ] Set budget alerts at 50/80/100% of the monthly forecast.
- [ ] Re-run this model after the first production month and compare forecast
      vs actual; record variance and update assumptions.
- [ ] Add AI cost metering before enabling AI features.

## Response to a cost spike

Follow runbook 12. In order: identify the driver, apply quotas, reduce capture
or retention, right-size workers, then fix the underlying loop or regression.
Do not disable security controls (SSRF validation, rate limits, backups) to cut
cost.
