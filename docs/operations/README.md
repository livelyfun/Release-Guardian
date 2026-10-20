# Operations

Operational guidance for Release Guardian. These documents are written to be
executed, not just read: every alert maps to a runbook, every drill has a
reproducible command, and every SLO has a measurement query.

| Document | Purpose |
|---|---|
| [SLI-SLO.md](SLI-SLO.md) | Service level indicators, provisional objectives, error budgets, RTO/RPO |
| [RUNBOOKS.md](RUNBOOKS.md) | 14 detection/containment/recovery runbooks |
| [LOAD-AND-RESILIENCE.md](LOAD-AND-RESILIENCE.md) | Load test methodology, local baseline, resilience drills |
| [BACKUP-RESTORE.md](BACKUP-RESTORE.md) | Backup policy, restore drill, rollback drill |
| [SECURITY-REVIEW.md](SECURITY-REVIEW.md) | Threat-to-control evidence, residual risks, sign-off checklist |
| [COST-VALIDATION.md](COST-VALIDATION.md) | Cost drivers, model inputs, validation checklist |
| [PRODUCTION-CHECKLIST.md](PRODUCTION-CHECKLIST.md) | Go-live gate for M8 |

## Status

M8 deliverables are implemented and locally verified where possible. The M8
exit criterion — *documented SLOs met in staging; restore and rollback drills
pass* — requires a deployed staging environment and is **not yet signed off**.
See [PRODUCTION-CHECKLIST.md](PRODUCTION-CHECKLIST.md) for the outstanding
evidence.

## Reproducible commands

From the repository root:

```bash
make load-test                 # local API + inline worker + fixture target
make drill-backup              # Postgres dump/restore into a scratch database
make drill-resilience          # stop/start the worker during a queued run
make security-scan             # secret scan (exits non-zero on findings)
make cost-model                # illustrative monthly cost model
```

Drills that need Docker or a deployed stack document their prerequisites in
the linked runbook or operations document.
