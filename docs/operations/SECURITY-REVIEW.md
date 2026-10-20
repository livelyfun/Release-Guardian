# Security Review

**Type:** Engineering self-review against
[08-SECURITY-AND-THREAT-MODEL.md](../master-plan/release-guardian/08-SECURITY-AND-THREAT-MODEL.md)
**Date:** 2026-10-20
**Status:** Controls implemented and tested locally; external penetration test
and egress-firewall verification are still required before production sign-off.

## Method

1. Walk the threat table in doc 08 and map each threat to code and tests.
2. Review every place user input reaches the network (`url_guard`, browser,
   Lighthouse, webhooks, artifacts).
3. Review authentication, authorization, secret handling, and error responses.
4. Run the security-relevant test suites and the secret scanner.
5. Record residual risk with an owner and follow-up.

## Threat-to-control evidence

| Threat | Control | Evidence |
|---|---|---|
| SSRF via HTTP checks | Scheme/host allowlist, DNS resolution, private/loopback/link-local/metadata rejection, redirect-chain validation | `backend/app/services/url_guard.py`, `_fetch_with_redirects` in `services/checks.py`, `test_url_guard_blocks_metadata_address` |
| SSRF via browser subresources | Every navigation/XHR/subresource is validated; blocked requests are aborted and recorded; `data:`/`blob:`/`about:` are allowed | `perform_browser_check` route guard, `blocked_requests` evidence |
| SSRF via Lighthouse | Target validated before launching Chrome | `perform_lighthouse_check` → `validate_url` |
| Cross-tenant leakage | Server-side role checks on every workspace-scoped route; 404 for foreign resources; tenant-scoped queries | `api/v1/deps.py`, `api/v1/access.py`, `test_tenant_isolation_between_users` |
| Credential leakage in logs | JSON logger records `request_id`, run/monitor ids only; no tokens/passwords; error handler returns generic 500 | `core/observability.py`, `core/errors.py` |
| Secrets in configuration | Regex scanner with masked output; production startup refuses default/weak secrets | `services/secret_scanner.py`, `core/production.py`, `test_production_config_guard_flags_defaults` |
| Password compromise | scrypt (N=2^14) with per-user salt and constant-time comparison | `core/security.py` |
| Token forgery/replay | HS256 JWT with `iat`/`exp`/`jti`; access/refresh type separation; production secret guard | `create_token`, `decode_token`, `production.py` |
| API key exposure | 256-bit random key, only SHA-256 hash stored, display prefix retained, revocation supported | `services/slug.py`, `endpoints/api_keys.py` |
| Webhook spoofing (outgoing) | HMAC-SHA256 over `timestamp.body` with `X-RG-Signature` and `X-RG-Timestamp`; target URL passes SSRF validation | `core/security.sign_webhook`, `notifications/webhook.py` |
| Artifact URL leakage | Workspace authorization before signing; URL TTL 900s; unguessable keys | `endpoints/artifacts.py`, `services/storage.py`, `ARTIFACT_URL_TTL_SECONDS` |
| Abuse / DoS | Per-identity rate limits (Redis shared, memory fallback); per-monitor and per-workspace active-run ceilings; run/step timeouts; Celery time limits | `core/rate_limit.py`, `services/capacity.py`, `celery_app.py` |
| Browser escape | Worker runs as UID 10001, `no-new-privileges`, all caps dropped, PID limit, tmpfs `/tmp`, `--no-sandbox` only inside isolated container | `Dockerfile.worker`, `docker-compose.yml` |
| Metrics disclosure | `/metrics` can require `Authorization: Bearer $METRICS_TOKEN`; disabled returns 404 | `main.py`, `test_metrics_token_protects_endpoint` |
| Error detail leakage | Structured error envelope; unexpected exceptions return `Internal server error` | `core/errors.py` |
| CORS | Explicit origin list; wildcard rejected by production guard | `main.py`, `production.py` |

## Findings fixed during this review

| Finding | Impact | Fix |
|---|---|---|
| Lighthouse executed without validating the target | SSRF via Lighthouse | Validate before launching; production guard for private URLs |
| Browser subresources bypassed URL validation | SSRF via iframe/XHR | Route-level validation and `blocked_requests` evidence |
| `storage.py` referenced missing imports (`settings`, `ClientError`) | Artifact failures/NameError | Correct imports, optional-boto3 fallback, metrics |
| Secret scanner referenced undefined `results` | Security check crashed | Rewritten scanner with masked findings and CLI exit code |
| Artifact signed URLs valid for 7 days | Long-lived bearer URLs | Reduced to 900 s (configurable) |
| Signed URL endpoint checked workspace but not artifact ownership | Cross-tenant URL if a key leaked | Resolve artifact → run → environment → project; 404 on mismatch |
| In-memory rate limits per API replica | Quota bypass by replica fan-out | Redis-backed shared limiter with fallback |
| Default secrets allowed in production | Token/signature forgery | Startup refusal via `production.py` |
| Duplicate run execution on redelivery | Duplicate incidents/usage | Per-run Redis lock + terminal-status guard |
| API container ran as root | Larger blast radius | Non-root UID 10001 |
| `/ready` returned raw DB/Redis exceptions | Internal host/credential detail leak | Log detail server-side; probe returns `error` |
| Metrics labeled by raw unmatched paths | Unbounded cardinality / memory growth | Unmatched requests share `<unmatched>` |
| Unvalidated artifact key could acquire a signed URL | Cross-tenant bearer URL | Ownership lookup before signing |
| Backup drill interpolated `DRILL_DB` into SQL | Accidental/injected identifier | Strict identifier validation + `umask 077` dumps |
| Uppercase `ENVIRONMENT=Production` bypassed the startup guard | Unsafe production boot | Normalize `environment`/`worker_mode`/`rate_limit_backend`; guard rejects unknown limiter backends |

## Residual risks

| # | Risk | Severity | Owner | Mitigation / next step |
|---|---|---|---|---|
| R1 | SSRF DNS rebinding/TOCTOU between validation and connection | High | Platform | Enforce egress firewall allowlist and connection-time IP filtering; document as deployment requirement |
| R2 | Artifacts/screenshots may contain PII or tokens rendered on the page | High | Product/Security | Add retention limits, redaction rules, and access auditing; restrict bucket to private |
| R3 | No individual access-token revocation (only JWT-secret rotation) | Medium | Backend | Add `jti` denylist/`token_version` per user |
| R4 | Email notifier is a stub that always errors | Medium | Backend | Wire an SMTP/provider transport before enabling email channels |
| R5 | Dependency/SBOM scanning not in CI | Medium | Platform | Add `pip-audit`, `npm audit --omit=dev`, and image SBOM generation |
| R6 | Secret scanner is regex-only and can miss novel formats | Medium | Security | Add provider-specific patterns and run against build artifacts, not just runtime env |
| R7 | Rate limiting falls back to per-process memory during Redis outage | Medium | Platform | Alert on `rate_limit_redis_unavailable`; accept degraded quota during outage |
| R8 | S3 bucket policy/IAM is not codified in this repo | Medium | Platform | Provision private bucket, block public access, least-privilege keys; documents in infra repo |
| R9 | No application-layer WAF/DDoS protection | Medium | Platform | Terminate at an edge with WAF/rate limits; keep `/metrics` private |
| R10 | Browser isolation depends on container runtime settings | Medium | Platform | Run workers on dedicated nodes with seccomp/AppArmor and egress policy |

## Verification commands

```bash
cd backend
.venv/bin/ruff check app tests
.venv/bin/pytest -q
.venv/bin/python -m app.services.secret_scanner
```

The CI workflow runs lint, tests, and the secret scan. Run the scanner against
production configuration in a secure environment; it prints only masked values
and exits non-zero on high/critical findings.

## Production sign-off checklist

- [ ] Egress firewall allowlist enforced for API and browser workers (R1).
- [ ] Dedicated browser worker pool with seccomp/AppArmor and resource caps.
- [ ] TLS everywhere; HSTS at the edge; no plaintext internal traffic.
- [ ] `JWT_SECRET`, `WEBHOOK_SIGNING_SECRET`, DB and S3 credentials in a secret
      manager; rotation procedure tested.
- [ ] `/metrics` protected by token or private network.
- [ ] S3 bucket private, public access blocked, versioning/lifecycle set.
- [ ] Dependency and image scanning enabled; no high/critical findings.
- [ ] External penetration test completed; findings triaged.
- [ ] Incident response contacts and legal notification path confirmed.
- [ ] Backup/restore and rollback drills passed (link evidence).
