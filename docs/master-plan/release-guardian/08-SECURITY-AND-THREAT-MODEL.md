# 08 — SECURITY AND THREAT MODEL

**Status:** Planning-only | **Date:** 2026-10-19

## Top Threats

| Threat | Vector | Impact | Controls |
|---|---|---|---|
| SSRF | User-supplied URLs, redirects, DNS rebinding, IPv6, WebSockets, subresources | High | Strict validation, IP resolution, redirect chain validation, egress policy, block private/loopback/link-local/metadata, browser network restrictions |
| Browser escape/untrusted content | Visited pages (JS), iframes, downloads | High | Isolated containers, resource caps, non-root, tmpfs/RO FS, cleanup, separate worker pools |
| Cross-tenant leakage | API/DB/artifacts/access | High | Server-side authZ, tenant-scoped queries, RLS (defense-in-depth), signed URLs scoped to tenant/project, audit logs |
| Credential leakage | Logs/artifacts/HAR/console/screenshots | High | Redaction, encryption at rest, secrets store, no secrets logged, hash-only for keys |
| Webhook abuse | GitHub webhooks, replay, spoofing | Med-High | Signature verification, timestamp/replay window, delivery idempotency, IP allowlists (where feasible) |
| Abuse/DoS | Job spam, large journeys | Med | Quotas, concurrency caps, timeouts, rate limits, backpressure |

## SSRF: Enforced Network Boundaries

**Connection-time validation (before connect):**
- Scheme allowlist: `http`, `https` only. Reject others (file, ftp, data, ws/wss handled separately with policy).
- Host validation: block localhost variants, private ranges (RFC 1918 10/8,172.16/12,192.168/16), link-local (169.254/16), unique local (fc00::/7), CGNAT (100.64/10), documentation/test (192.0.2/24,198.51.100/24,203.0.113/24), IPv6 loopback (::1), IPv6 link-local (fe80::/10), metadata endpoints (cloud metadata IPs/domains).
- DNS resolution: resolve once at connection time; if multiple IPs returned, validate all (or enforce policy per IP) and consider TTL/reuse constraints. Do not trust client-supplied IPs.
- Redirect validation: treat each redirect as new destination; re-validate scheme/host/IP, enforce max redirect depth, disallow redirecting to blocked targets. Log blocked redirects with evidence.
- DNS rebinding: re-check IP after resolution at request time or enforce short DNS cache + re-validation on redirects; block if IP changes to private/blocked. 
- IPv6: full parsing; block ULA/link-local/loopback.

**Network-layer enforcement:**
- Egress policy: default deny to private/internal ranges from browser worker containers; optional per-workspace allowlists (explicit, justified) require approval path.
- Browser restrictions: block or restrict subresource requests to blocked ranges (frame sources, XHR/fetch), WebSocket connections subject to same policy, disallow access to browser-internal/metadata. Consider disabling certain capabilities.
- Timeouts: connection timeout, DNS timeout, total request timeout, idle timeout.

**Monitoring:** Blocked attempts logged (tenant/project/check, reason, host/IP, redirect chain) to audit log; alert on spikes.

## Redaction & PII

- Strip secrets/tokens from console logs, HAR (request/response bodies selectively), screenshots (avoid capturing sensitive forms), step evidence. 
- Credentials encrypted at rest (KMS-backed if available); API keys stored as hashes only. 
- Audit logs avoid PII where possible.

## Tenant Isolation

- Server-side authZ on every resource; tenant scope derived from session/key + workspace membership. 
- DB queries must include workspace_id filter (and RLS as defense-in-depth). 
- Signed artifact URLs scoped to tenant/project, short expiry, access logged. 
- Cross-tenant negative tests required.

## Secrets & Key Management

- Platform secret store; rotation plan, least privilege. 
- No secrets in logs/images/env values printed. 
- Webhook secrets, integration tokens encrypted. 

## Compliance & Hardening

- Least privilege containers (non-root), read-only FS, tmpfs, seccomp/AppArmor (where available), resource limits. 
- Dependency scanning (SCA), SBOM (track deps), renovate/dependabot. 
- Incident runbooks, on-call checklist.
