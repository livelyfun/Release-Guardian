# 00 — MASTER PLAN

**Project:** Release Guardian  
**Status:** Implementation in progress (engineering foundation, identity, execution, monitoring)  
**Date:** 2026-10-19  
**Scope:** Multi-tenant website reliability, synthetic monitoring, and release verification

## Executive Summary

Release Guardian is a multi-tenant platform for validating website behavior via real-browser checks, detecting regressions, correlating failures with deployments, and collecting diagnostic evidence. The core remains deterministic; AI, if enabled, is advisory.

## Operating Principles

- Evidence before conclusions (verified fact, recommendation, assumption, unknown, owner decision)
- Planning only (no code changes, deps, infra, deploys)
- Tenant isolation by default (server-side authZ + defense-in-depth)
- SSRF/browser execution treated as high-risk and explicitly controlled
- Preserve existing project documentation

## Architecture Decision (Summary)

**Recommended:** Managed hybrid (Vercel + managed containers/workers + Neon Postgres + Redis + S3-compatible storage). Modular monolith API (FastAPI) with isolated browser workers (Playwright + Lighthouse). Queue-based execution (Celery/RQ). See [03-TECHNOLOGY-DECISIONS.md](03-TECHNOLOGY-DECISIONS.md) for full matrix.

## Documentation Index

1. [00-MASTER-PLAN.md](00-MASTER-PLAN.md) — this document
2. [01-PRODUCT-REQUIREMENTS.md](01-PRODUCT-REQUIREMENTS.md)
3. [02-FEATURE-CATALOG.md](02-FEATURE-CATALOG.md)
4. [03-TECHNOLOGY-DECISIONS.md](03-TECHNOLOGY-DECISIONS.md)
5. [04-SYSTEM-ARCHITECTURE.md](04-SYSTEM-ARCHITECTURE.md)
6. [05-DATA-MODEL.md](05-DATA-MODEL.md)
7. [06-API-AND-EVENT-CONTRACTS.md](06-API-AND-EVENT-CONTRACTS.md)
8. [07-QUEUE-SCHEDULER-AND-WORKERS.md](07-QUEUE-SCHEDULER-AND-WORKERS.md)
9. [08-SECURITY-AND-THREAT-MODEL.md](08-SECURITY-AND-THREAT-MODEL.md)
10. [09-TEST-AND-QUALITY-STRATEGY.md](09-TEST-AND-QUALITY-STRATEGY.md)
11. [10-DEPLOYMENT-AND-CICD.md](10-DEPLOYMENT-AND-CICD.md)
12. [11-OBSERVABILITY-AND-OPERATIONS.md](11-OBSERVABILITY-AND-OPERATIONS.md)
13. [12-AI-ENGINEERING-AND-EVALUATION.md](12-AI-ENGINEERING-AND-EVALUATION.md)
14. [13-COST-AND-CAPACITY-MODEL.md](13-COST-AND-CAPACITY-MODEL.md)
15. [14-IMPLEMENTATION-ROADMAP.md](14-IMPLEMENTATION-ROADMAP.md)
16. [15-RISK-REGISTER.md](15-RISK-REGISTER.md)
17. [16-OPEN-DECISIONS.md](16-OPEN-DECISIONS.md)
18. [17-SOURCE-REGISTER.md](17-SOURCE-REGISTER.md)

## Critical Path

D (Execution + Checks) → E (Deployment Verification + Baselines + Incidents). Security gates (SSRF/tenant isolation) required before production exposure.
