# Security policy

Release Guardian runs user-supplied URLs through real browsers and stores the
resulting evidence, so a vulnerability here can expose more than a typical CRUD
app. Reports are welcome and taken seriously.

## Supported versions

Release Guardian is pre-1.0 and moving quickly. Only the tip of `main` is
supported. There are no backports or patch releases for older commits.

## Reporting a vulnerability

**Do not open a public issue, pull request, or discussion for a vulnerability.**

Use GitHub's private vulnerability reporting:

1. Open the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Describe the issue with enough detail to reproduce it.

Private reporting keeps the report visible only to the maintainers until a fix
is available and an advisory can be published.

Please include, where applicable:

- affected component (API, dashboard, worker, browser worker, scheduler);
- the exact version or commit;
- reproduction steps or a proof of concept;
- impact, and any preconditions (for example, an authenticated account or a
  specific role);
- whether the issue requires a non-default configuration.

## What is in scope

- Authentication, session handling, and token lifecycle.
- Authorization and cross-tenant isolation (workspace, project, environment,
  monitor, run, artifact).
- SSRF defenses: URL validation, redirect handling, DNS rebinding, browser
  subresource interception, and Lighthouse target handling.
- Browser-worker isolation and escape from the container sandbox.
- Artifact access control and signed-URL scope or lifetime.
- Secret handling, logging of sensitive values, and error responses that leak
  internals.
- Dependency vulnerabilities with a demonstrated impact on Release Guardian.

## What is out of scope

- Findings that require `ALLOW_PRIVATE_URLS=true` or another
  deliberately-insecure setting. That flag exists for local fixtures.
- Missing hardening headers on a deployment that sits behind a proxy you
  control, unless the application itself can prevent the issue.
- Self-hosted deployments that skipped the network-isolation requirements in
  [docs/operations/PRODUCTION-DEPLOYMENT.md](docs/operations/PRODUCTION-DEPLOYMENT.md).
- Denial of service through bulk scanning or load testing against third-party
  sites. Do not test against infrastructure you do not own.
- Reports produced solely by an automated scanner with no demonstrated impact.

## What to expect

This is a volunteer-maintained project with no security SLA and no guaranteed
response time. Reports are triaged on a best-effort basis. Confirmed issues are
fixed on `main` and, where appropriate, disclosed in a GitHub security advisory
with credit to the reporter unless you ask to remain anonymous.

Please give maintainers a reasonable opportunity to ship a fix before any public
disclosure.
