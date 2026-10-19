# RELEASE GUARDIAN
## Principal Engineering Council — Complete Product, Architecture, Automation & Deployment Master Plan

**Document type:** Master engineering instruction for OpenCode  
**Project codename:** Release Guardian  
**Objective:** Design a complete, production-grade, multi-tenant website reliability, automated testing, and deployment verification platform  
**Engagement mode:** Discovery, research, architecture, and comprehensive planning only  
**Implementation status:** Not authorized until the owner approves the plan

---

# 1. YOUR ROLE AND MANDATE

Act as a coordinated council of principal-level engineering experts working together to design Release Guardian.

You are not acting as a junior developer implementing isolated tasks. You are collectively responsible for the product's technical direction, architecture, security, engineering quality, deployment strategy, operational reliability, and long-term maintainability.

Adopt the perspectives of these specialists:

1. **Principal Software Architect:** system boundaries, architecture, scalability, trade-offs, technology selection, and architectural decision records.
2. **Principal Full-Stack Engineer:** frontend architecture, backend design, API contracts, application state, accessibility, and developer experience.
3. **Principal Python Engineer:** automation engines, browser execution, workers, orchestration, testing frameworks, and data processing.
4. **Principal DevOps and Platform Engineer:** environments, containers, infrastructure, CI/CD, deployment safety, infrastructure as code, and resource management.
5. **Principal SRE:** service-level objectives, failure recovery, capacity planning, monitoring, incident response, and disaster recovery.
6. **Principal Application Security Engineer:** threat modeling, multi-tenant isolation, identity, permissions, secret management, SSRF defense, sandboxing, and supply-chain security.
7. **Principal Test Automation Architect:** browser journeys, deterministic tests, test isolation, regression detection, failure evidence, and test reliability.
8. **Principal AI Engineer:** evidence-grounded diagnosis, optional AI-assisted troubleshooting, evaluation, security boundaries, privacy, and model governance.
9. **Principal Database Engineer:** data modeling, transactions, migrations, indexing, retention, concurrency, and database recovery.
10. **Principal Product Engineer:** customer needs, product differentiation, feature prioritization, usability, and measurable outcomes.
11. **Principal Prompt and Agent Workflow Engineer:** effective OpenCode instructions, safe tool usage, delegated research, reproducible workflows, and prevention of unsupported assumptions.
12. **Principal Technical Lead:** integration of all specialties into one coherent architecture, resolution of conflicting recommendations, and enforcement of project-wide standards.

These are analytical responsibilities, not a requirement to create twelve separate agents.

Use OpenCode subagents for focused, independent reviews when available and useful. Delegate research or audits where doing so reduces blind spots. Keep one lead architect accountable for the final design.

Do not simulate agreement between experts. Identify genuine disagreements, evaluate the trade-offs, and recommend a resolution.

# 2. OPERATING CONTRACT — NON-NEGOTIABLE

## 2.1 Planning only

During this engagement:

- Inspect the existing repository and environment.
- Research current technical documentation.
- Define the complete product specification.
- Evaluate and select the recommended architecture.
- Produce a comprehensive implementation and deployment roadmap.
- Create planning documents only if filesystem-write permissions explicitly allow them.
- Do not implement application features.
- Do not modify application source code, dependency manifests, lockfiles, application configurations, database schemas, or infrastructure definitions.
- Do not install packages or upgrade dependencies.
- Do not run database migrations.
- Do not connect to production services or change production state.
- Do not create, delete, or modify cloud resources.
- Do not trigger deployment workflows.
- Do not commit, reset, stash, or discard existing changes.
- Never overwrite existing project documentation without an explicit reason and authorization.

If OpenCode is running with read-only permissions, preserve that boundary. Produce the proposed documentation structure and content in the final response instead of bypassing permissions.

## 2.2 Evidence before conclusions

Distinguish among:

- **Verified fact:** confirmed from repository contents, executed read-only checks, or authoritative documentation.
- **Recommendation:** the engineering council's preferred decision.
- **Assumption:** a working hypothesis that needs validation.
- **Unknown:** information that could not be established.
- **Owner decision:** a decision that requires the project's owner to approve a meaningful trade-off.

Never claim that code, infrastructure, services, credentials, integrations, benchmarks, or deployments exist unless verified.

Never invent environment variables, cloud resources, API credentials, URLs, database contents, or successful test results.

## 2.3 Preserve existing work

Before investigating the repository:

1. Confirm the working directory.
2. Inspect the current Git branch and working-tree status.
3. Identify existing user changes and untracked files.
4. Inspect the project structure and repository instructions.
5. Identify the current framework, package managers, test commands, deployment setup, and existing architecture.
6. Record the baseline before recommending any changes.

Never assume the repository is empty or that it already belongs to Release Guardian.

If the repository contains an unrelated application, treat it as the current working environment, not as permission to repurpose that application.

## 2.4 No premature clarification

Make reasonable engineering assumptions and document them.

Do not interrupt the discovery process with repeated questions. Complete as much of the analysis as the available evidence permits.

If a genuine owner decision blocks the final recommendation, present the decision, viable options, trade-offs, preferred option, and consequences. Continue the rest of the plan.

# 3. PRODUCT DEFINITION

Release Guardian is a multi-tenant website reliability, synthetic monitoring, and release verification platform.

It allows individual developers, teams, agencies, and businesses to register multiple projects and environments, configure automated checks, execute real-browser tests, detect failures and regressions, correlate failures with deployments, and investigate incidents through collected evidence.

Its primary job is:

**Determine whether a monitored website is functioning correctly, detect meaningful changes from its expected behavior, and provide actionable evidence when something fails.**

The product is not simply a Lighthouse dashboard, an analytics platform, an uptime checker, or a wrapper around an AI model.

## 3.1 Core product workflow

Design around this workflow:

1. A user creates an account and workspace.
2. The user registers a project.
3. The user connects one or more environments, such as staging and production.
4. The user selects the checks and customer journeys that matter.
5. The platform schedules or receives a deployment event.
6. Jobs are validated, queued, prioritized, and executed by appropriate workers.
7. Results, logs, metrics, and evidence are stored.
8. The platform evaluates assertions, baselines, severity, and incident policies.
9. Notifications are delivered to configured destinations.
10. Developers inspect failures, compare releases, acknowledge incidents, and investigate the cause.
11. Successful and failed executions contribute to a reliable history of application behavior.

## 3.2 Product differentiation

Explicitly design features around these distinctions:

- Google Analytics primarily describes user activity and behavioral outcomes.
- Lighthouse evaluates selected page characteristics in a controlled audit.
- Uptime monitoring establishes whether endpoints respond.
- Release Guardian combines configurable browser-level behavior checks, scheduled synthetic monitoring, deployment-aware verification, historical comparison, incident management, and diagnostic evidence.

Do not claim these capabilities are unique in the market without researching existing competitors.

Research competing products and identify realistic differentiation opportunities, such as ease of configuring critical user journeys, deploy-aware testing, actionable diagnostics, flexible hosting, or a developer-focused experience.

The product must remain useful without an AI model. Core checks, assertions, rules, alerting, and incident state transitions must be deterministic wherever feasible.

# 4. DISCOVERY AND RESEARCH

## 4.1 Repository discovery

Inspect applicable files and metadata, including:

- `AGENTS.md`, `CLAUDE.md`, contribution instructions, and architecture documentation.
- Repository tree and package boundaries.
- `package.json`, Python project manifests, lockfiles, and workspace configuration.
- Framework and runtime versions.
- Existing tests and quality checks.
- Dockerfiles, Compose files, and infrastructure definitions.
- GitHub Actions workflows.
- Deployment configuration and provider manifests.
- Database schemas and migrations.
- Environment-variable names and example files.
- Existing authentication, API, queue, monitoring, logging, and error-reporting integrations.
- Current implementation limitations and uncommitted work.

Never print secret values from `.env` files or similar sources. If checking secrets, report only the presence or absence of expected variable names.

Avoid traversing enormous build directories or reading sensitive files that are unnecessary for planning.

## 4.2 Technical research

Use available OpenCode web-search and web-fetch tools where supported.

Prioritize official documentation, maintained project documentation, security advisories, and current compatibility information.

Research relevant documentation for:

- OpenCode agents, permissions, instructions, and MCP integrations.
- Next.js and TypeScript.
- Python and FastAPI.
- PostgreSQL and the selected managed database.
- Redis-compatible queues or a durable workflow engine.
- Playwright and browser-container isolation.
- Lighthouse and relevant web performance metrics.
- Docker and container security.
- Selected deployment providers.
- Authentication and authorization.
- GitHub Apps, webhooks, and Actions.
- Secret management and notification delivery.
- Observability and incident management.
- OWASP guidance, particularly SSRF prevention.
- Relevant accessibility, security, and web-platform standards.

Use the official references below as starting points, not as a substitute for verifying the actual design:

- OpenCode documentation: https://docs.opencode.ai/docs/
- OpenCode agents: https://docs.opencode.ai/docs/agents/
- OpenCode permissions: https://docs.opencode.ai/docs/permissions/
- Playwright CI: https://playwright.dev/docs/ci
- Playwright Docker: https://playwright.dev/docs/docker
- Lighthouse: https://developer.chrome.com/docs/lighthouse/
- FastAPI: https://fastapi.tiangolo.com/
- PostgreSQL: https://www.postgresql.org/docs/
- Temporal: https://docs.temporal.io/
- Docker: https://docs.docker.com/
- GitHub Actions: https://docs.github.com/en/actions
- GitHub deployment security: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments
- OWASP SSRF prevention: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

Verify that documentation is applicable to the proposed runtime, framework versions, and hosting plan.

Do not select a dependency merely because it is familiar or popular.

# 5. PRODUCT REQUIREMENTS — COMPLETE FEATURE INVENTORY

Design the whole intended product. Do not silently omit difficult modules simply to make the initial architecture easier.

For every feature, document its purpose, user value, dependencies, failure modes, security implications, API and data requirements, test strategy, and implementation phase.

## 5.1 Accounts, workspaces, and identity

Plan for:

- User registration and sign-in.
- Email verification and account recovery.
- Optional enterprise authentication or SSO if justified.
- Workspace creation and management.
- Invitations and membership lifecycle.
- Workspace ownership transfer.
- Role-based access control.
- Project-level permissions where useful.
- Session management, logout, and revocation.
- Audit logs for sensitive administrative actions.
- Account and workspace deletion workflows.
- Protected administrative operations.

Propose a sensible role model, including owner, administrator, developer, and read-only viewer.

Explain which permissions are workspace-wide and which are project-specific.

## 5.2 Organization and project management

Support:

- Multiple workspaces per user where appropriate.
- Multiple projects per workspace.
- Multiple environments per project.
- Production, staging, preview, and custom environments.
- Project metadata, repository links, deployment links, and ownership.
- Environment-specific URLs and monitoring policies.
- Project tagging and filtering.
- Search, sorting, and grouping.
- Project archival and deletion.
- Project-specific alert and retention settings.

## 5.3 Website and endpoint monitoring

Design checks for:

- HTTP and HTTPS availability.
- Expected status codes.
- Response latency and timeout thresholds.
- DNS resolution.
- TLS certificate validity and expiration.
- Redirect chains.
- Important page availability.
- Expected or missing content.
- Selected response-header policies.
- Broken links and bounded site crawling.
- Robots.txt and sitemap accessibility.
- Scheduled checks and on-demand runs.
- Check-frequency configuration.
- Regional checks, if needed.
- Maintenance windows.
- False-positive control and consecutive-failure policies.

Distinguish a failed target from a failed monitoring worker, a provider outage, a DNS failure, or an invalid test configuration.

## 5.4 Real-browser synthetic testing

Use Playwright or an equivalent verified browser automation framework.

Support a safe, maintainable test-definition model for:

- Opening a page.
- Navigating between routes.
- Locating elements.
- Clicking buttons and links.
- Filling forms.
- Selecting options.
- Waiting for expected states.
- Asserting visible text and element state.
- Checking URLs and navigation outcomes.
- Inspecting browser console errors.
- Detecting failed network requests.
- Capturing screenshots.
- Capturing traces and diagnostic artifacts.
- Recording per-step timing.
- Retrying only where semantically safe.

Plan critical customer journeys, such as:

- Contact form submission.
- Login using a dedicated test account.
- Account registration where appropriate.
- Booking inquiry.
- Search and filtering.
- Checkout in a sandbox environment.
- Authenticated dashboard access.
- Form validation and confirmation flows.

Never test real payments, send real customer messages, or create uncontrolled production data by default.

Provide a safe test-data strategy and cleanup procedures.

Do not expose arbitrary Python or JavaScript execution to customers inside the normal control plane. Prefer a constrained test DSL or declarative test builder. If custom-code testing becomes necessary, design an isolated runner with strict resource and network policies.

## 5.5 Performance, accessibility, and technical SEO

Integrate established tools rather than rebuilding their functionality unnecessarily.

Plan for:

- Automated Lighthouse audits.
- Configurable performance thresholds.
- Relevant lab measurements and Core Web Vitals lab metrics.
- Optional real-user monitoring as a separately scoped capability.
- Technical SEO checks.
- Metadata and canonical-tag validation.
- Sitemap and robots.txt checks.
- Structured-data validation where appropriate.
- Accessibility audits.
- Broken-link detection.
- Historical comparisons.
- Threshold-based regression detection.
- Environment- and page-specific audit policies.

Clearly distinguish lab results from real-user measurements. A simulated test must never be presented as proof of actual visitor experience.

Define how the platform selects pages, limits crawl scope, manages browser resources, stores audit evidence, and handles unstable results.

## 5.6 Deployment and release verification

Plan integrations with GitHub and deployment platforms through supported APIs and webhooks.

Include:

- Repository connection and permission management.
- Deployment event ingestion.
- Commit, branch, pull-request, and deployment identifiers.
- Environment association.
- Post-deployment smoke tests.
- Configurable critical-journey suites.
- Comparison with a previous known-good release.
- Version-aware test history.
- Regression detection.
- Optional pull-request status checks.
- CI pipeline integration.
- Release verification reports.
- Deploy-to-incident correlation.
- Manual approval or review gates for high-risk actions.

Define clear release states, such as pending, running, passed, failed, and inconclusive.

Do not interpret deployment success as proof that the application works.

Do not automatically roll back production or change customer infrastructure without an explicit, authorized policy. Keep recovery recommendations and actual rollback execution separate.

## 5.7 Baselines and regression detection

Define:

- What constitutes a baseline.
- Which previous runs qualify as healthy.
- How to handle first-time checks.
- How many samples are needed before comparing noisy metrics.
- Fixed thresholds versus statistical anomaly detection.
- Performance regression tolerances.
- Functional failures that bypass performance tolerances.
- How to identify flakiness.
- How to account for environment differences.
- How to distinguish an application regression from monitoring infrastructure noise.
- How users can acknowledge or suppress known exceptions.
- How baselines can be reset safely.

Do not blindly compare every measurement with the immediately preceding run.

## 5.8 Incident management

Include:

- Incident creation and lifecycle.
- Severity assignment.
- Alert deduplication.
- Grouping related failures.
- Acknowledgement and resolution.
- Incident timelines.
- Maintenance windows.
- Escalation policies.
- Notification retries.
- Suppression rules.
- Runbook links.
- Links to affected deployments.
- Diagnostic evidence and attachments.
- Post-incident reporting.

Define how incidents move between states and prevent repeated identical failures from producing unlimited notifications.

## 5.9 Notifications and integrations

Design a provider-independent notification interface where useful.

Evaluate:

- Email.
- Webhooks.
- Slack or similar messaging services.
- Microsoft Teams or equivalent integrations.
- GitHub checks and comments where permissions allow.
- Optional issue creation.
- Optional incident-management service integrations.

For every integration, specify authorization, required scopes, event validation, retries, rate limits, failure handling, and secret rotation.

Do not assume an integration is already configured.

## 5.10 Reporting and dashboards

Plan the following user experiences:

- Workspace overview.
- Project and environment overview.
- Current service health.
- Recent incidents.
- Recent deployment status.
- Monitoring history.
- Test-run details.
- Step-by-step browser test results.
- Screenshots, logs, and traces.
- Performance trends.
- Regression comparisons.
- Uptime reports.
- Filters and date ranges.
- Exportable reports.
- Team activity and audit logs.
- Usage and resource consumption.

Design for desktop productivity and responsive mobile access.

Follow accessible interaction patterns, keyboard navigation requirements, semantic markup, and useful loading, empty, error, and permission-denied states.

Do not prioritize decorative dashboards over the clarity and reliability of diagnostic information.

## 5.11 Public API, CLI, and developer experience

Evaluate and plan:

- A documented versioned REST API.
- API keys or appropriate machine-to-machine authentication.
- Scoped credentials and revocation.
- Rate limits.
- Idempotency for mutation and job-submission endpoints.
- Webhook delivery and signature verification.
- API pagination and consistent error formats.
- OpenAPI documentation.
- SDK generation if useful.
- CLI for initiating checks and querying results.
- CI-friendly commands and exit codes.
- Example integrations.
- Local development documentation.
- Troubleshooting documentation.

## 5.12 AI-assisted diagnosis

AI is an optional assistance layer, not the authority that decides whether a check passed.

Evaluate an AI assistant that can:

- Summarize verified test failures.
- Explain likely causes with references to specific evidence.
- Compare failure patterns across deployments.
- Suggest troubleshooting steps.
- Draft an incident report.
- Propose a test from a natural-language description.
- Generate a proposed code change or pull request for human review.
- Answer questions about authorized project history.

Design explicit boundaries:

- The deterministic testing engine remains the source of truth.
- AI output is marked as a hypothesis or recommendation.
- Every diagnosis must reference the available evidence.
- The model must report insufficient evidence rather than inventing a cause.
- Browser output, website content, logs, and user-submitted text are untrusted inputs.
- Untrusted content must never acquire tool permissions or override system instructions.
- Secrets, cookies, tokens, and unnecessary personal data must be redacted before external model calls.
- Customer data must not be shared with external model providers without the configured policy and necessary authorization.
- Model access, spending, retries, quotas, and timeouts must be controlled.
- AI-generated code must not be deployed automatically.
- AI functionality must degrade gracefully when providers fail.

Evaluate whether the initial deployment should include AI or whether the evidence model and integrations should be completed first.

## 5.13 Billing and commercial SaaS readiness

Evaluate the requirements for a commercial product.

Plan for:

- Plan definitions.
- Project and environment limits.
- Check-frequency limits.
- Worker-minute or execution-usage metering.
- Browser concurrency limits.
- Retention limits.
- Notification quotas.
- Subscription state.
- Invoice and payment integration where supported.
- Usage dashboards.
- Upgrade and downgrade behavior.
- Grace periods and delinquency handling.
- Subscription cancellation.
- Abuse controls.
- Administrative overrides.

Keep billing provider-specific behavior isolated from core monitoring logic.

Verify supported countries, payment methods, fees, webhook behavior, and account requirements before selecting any payment provider.

Do not assume a particular pricing model or payment processor without recording the assumptions.

# 6. ARCHITECTURE DESIGN

## 6.1 Compare the alternatives

Evaluate at least three credible deployment and architecture options.

Include, at minimum:

**Option A — Managed hybrid platform**
- Managed web hosting.
- Container-based API and browser workers.
- Managed PostgreSQL.
- A compatible managed queue or Redis service.
- Managed object storage where needed.

**Option B — Containerized VPS**
- A Linux VPS or small cluster.
- Docker Compose or an appropriate container orchestrator.
- Reverse proxy and TLS.
- Application services, workers, and appropriately managed data services.
- Explicit backup, upgrade, recovery, and monitoring procedures.

**Option C — Cloud-native or higher-scale architecture**
- Container or service orchestration.
- Independently scalable worker pools.
- Durable workflow execution if justified.
- Managed data and observability infrastructure.
- Stronger isolation and advanced scaling controls.

Do not select the most complex option merely because it appears more enterprise-grade.

## 6.2 Decision matrix

Score the options using a weighted assessment:

| Criterion | Suggested weight |
|---|---:|
| Reliability and failure recovery | 20% |
| Security and browser isolation | 20% |
| Operational complexity | 15% |
| Scalability and concurrency | 15% |
| Cost and cost predictability | 10% |
| Developer productivity | 10% |
| Portability and exit costs | 5% |
| Observability and maintainability | 5% |

Adjust the criteria if evidence justifies a different weighting.

For each option, explain:

- Main advantages.
- Main disadvantages.
- Operational burden.
- Expected failure modes.
- Security implications.
- Cost drivers.
- Scaling limits.
- Migration path.
- Vendor lock-in.
- Suitability for this product.

Scores are engineering judgments, not measured benchmarks. State confidence and important assumptions.

## 6.3 Evaluate the recommended technology stack

Evaluate a baseline similar to the following, but validate every selection against the actual requirements.

**Frontend**
- Next.js.
- TypeScript.
- Accessible component system.
- Server-side authorization boundaries.
- Typed API client.
- Structured application error handling.

**Control plane**
- Python.
- FastAPI.
- Pydantic or equivalent validation.
- OpenAPI-backed contracts.
- A modular application architecture.
- Clear domain boundaries.

**Background execution**
- Python workers.
- Playwright.
- Lighthouse through supported tooling.
- Explicitly versioned job payloads.
- Queue-based execution.
- Per-job timeouts and resource limits.
- Retry policies appropriate to each job type.

**Persistence**
- PostgreSQL for durable application state.
- Redis or a compatible queue backend where appropriate.
- Object storage for retained artifacts.
- Transactional patterns to prevent lost or duplicated work.

**Local development**
- Docker Compose.
- Reproducible runtime versions.
- Local database and queue.
- Safe test-data fixtures.
- Documented setup commands.

**Delivery**
- GitHub.
- GitHub Actions or a justified alternative.
- Container image builds.
- Environment-specific deployment.
- Automated quality gates.

**Initial hosting candidate**
- Vercel for the Next.js frontend.
- Render or an equivalent container host for the API and persistent browser workers.
- Neon or an equivalent managed PostgreSQL service.
- A Redis-compatible managed queue service that has been verified to support the selected worker library's actual requirements.
- Object storage for browser evidence when needed.

Treat these providers as candidates, not mandatory commitments.

Verify provider regions, database connectivity, queue compatibility, connection limits, background-worker support, persistent storage, resource limits, execution timeouts, pricing, and service availability before finalizing the recommendation.

Prefer one cohesive initial architecture over unnecessary duplication between TypeScript and Python services.

## 6.4 Modular boundaries

Design clear logical modules, including:

- Identity and access control.
- Workspaces and memberships.
- Projects and environments.
- Monitoring configuration.
- Scheduling.
- Job dispatch and orchestration.
- HTTP and endpoint checks.
- Browser test execution.
- Performance and SEO auditing.
- Deployment integrations.
- Baseline and regression evaluation.
- Incident management.
- Notification delivery.
- Reporting.
- Usage and quotas.
- Billing.
- AI-assisted diagnosis.
- Administration and audit logging.

Choose a modular monolith for the control plane unless evidence supports a different design. Separate heavy browser execution from request-serving services.

Define when a component should become a separately deployed service and which boundaries should remain internal modules.

Do not adopt microservices merely to make the architecture diagram larger.

# 7. WORK QUEUE, SCHEDULER, AND AUTOMATION ENGINE

This is a core part of Release Guardian and deserves a complete design.

## 7.1 Compare execution technologies

Evaluate reasonable options, such as:

- Celery with a compatible broker.
- A simpler Python task queue.
- A durable workflow engine such as Temporal.
- Other justified queue or workflow technologies.

Compare operational complexity, retries, scheduling, delayed work, cancellation, durability, observability, resource isolation, and deployment compatibility.

Choose one recommended approach and explain when an alternative becomes worthwhile.

## 7.2 Scheduling

Define how the platform:

- Determines which checks are due.
- Schedules work across time zones.
- Handles missed schedules.
- Prevents duplicate schedules from enqueuing uncontrolled jobs.
- Applies workspace quotas.
- Supports manual and event-driven runs.
- Prioritizes deployment checks over routine checks where configured.
- Handles maintenance windows.
- Tracks last successful and last attempted checks.

The scheduler must not silently stop working.

## 7.3 Reliable execution

Design for:

- Idempotent job creation.
- Stable job identifiers.
- Versioned task payloads.
- Database-to-queue consistency.
- Bounded retries with backoff and jitter.
- Explicit terminal failure states.
- Cancellation where safe.
- Dead-letter handling or an equivalent mechanism.
- Worker heartbeats and health checks.
- Graceful shutdown.
- Reprocessing and administrative recovery.
- Queue-age monitoring.
- Per-workspace concurrency limits.
- Fair scheduling.
- Horizontal worker scaling.

Document at-least-once delivery assumptions, duplicate execution behavior, and the idempotency of result writes and incident creation.

Never claim exactly-once execution unless the complete mechanism and guarantees justify it.

## 7.4 Browser execution

Treat browser automation as a security-sensitive workload.

Design:

- Reproducible browser-worker images.
- Compatible browser and Playwright versions.
- Resource limits for CPU, memory, disk, and execution time.
- Process cleanup after completion or failure.
- Secure artifact collection.
- Isolation between customer jobs.
- Bounded screenshot and trace retention.
- Browser profile cleanup.
- Network egress restrictions.
- Safe handling of cookies, tokens, and test credentials.
- Worker replacement after suspected compromise or corruption.

Do not assume that placing a browser in a container automatically makes untrusted browsing safe.

# 8. DATA ARCHITECTURE

Produce a conceptual entity-relationship diagram and a detailed initial data model.

Evaluate entities similar to:

- User.
- Session or identity mapping.
- Workspace.
- Membership.
- Role and permission.
- Project.
- Environment.
- Monitored target.
- Check configuration.
- Test definition and version.
- Deployment.
- Audit run.
- Job and execution attempt.
- Step result.
- Metric sample.
- Artifact.
- Baseline.
- Incident.
- Incident event.
- Notification channel.
- Notification attempt.
- Integration installation.
- API credential.
- Usage record.
- Subscription.
- Audit-log entry.

For each entity, specify:

- Purpose.
- Primary key.
- Important relationships.
- Workspace or tenant association.
- Uniqueness constraints.
- Indexing and query patterns.
- Retention requirements.
- Deletion semantics.
- Sensitive information.
- Concurrency considerations.

Define:

- How tenant isolation is enforced in the database and application.
- How audit history is retained.
- Which large datasets may require partitioning later.
- How migrations are versioned and rolled out safely.
- Which results are immutable and which are mutable.
- How repeated runs are distinguished.
- How artifacts are referenced without exposing private storage.
- How data is deleted when an account or workspace is removed.

Do not overengineer partitioning or distributed database systems before projected workload justifies them.

# 9. API AND EVENT CONTRACTS

Define the principal API resources and operations.

Include families for:

- Authentication and workspace management.
- Members and invitations.
- Projects and environments.
- Monitors and checks.
- Test definitions.
- Test runs.
- Audit results and historical comparisons.
- Deployments and release checks.
- Incidents.
- Notification configuration.
- Integrations and webhooks.
- Usage.
- Reports.
- Administrative operations.

For each family, specify authorization, input validation, response shape, errors, pagination, idempotency, and rate limits.

Define the key internal events, including:

- Check scheduled.
- Job queued.
- Execution started.
- Execution completed.
- Execution failed.
- Deployment detected.
- Release verification completed.
- Regression detected.
- Incident opened.
- Incident acknowledged.
- Incident resolved.
- Notification delivery failed.

Plan event versioning and safe handling of duplicate or out-of-order events.

Document an OpenAPI contract strategy and a consistent error format.

Do not implement the API in this engagement.

# 10. SECURITY AND PRIVACY PLAN

Create a threat model before proposing production exposure.

## 10.1 SSRF and arbitrary website monitoring

Because the platform visits URLs supplied by users, SSRF is a fundamental product risk.

Design defenses at both the application and network layers.

Explicitly consider:

- Localhost and loopback addresses.
- Private IPv4 and IPv6 addresses.
- Link-local and metadata-service addresses.
- DNS rebinding.
- IPv4 and IPv6 parsing edge cases.
- Redirects to prohibited destinations.
- Subresource requests made by browser pages.
- WebSockets and non-HTTP protocols.
- Uncontrolled DNS lookups.
- URL parser inconsistencies.
- Egress to internal infrastructure.
- Access to control-plane and cloud credentials.
- Malicious websites attempting to compromise browser workers.

Use explicit scheme restrictions, destination validation, connection-time enforcement, redirect validation, and appropriate network-level egress controls.

Do not rely exclusively on a URL regex, initial DNS lookup, or blocked list.

If a robust and enforceable isolation model cannot be defined for arbitrary websites, narrow the supported behavior and document the restriction before deployment.

## 10.2 Tenant isolation

Prevent cross-workspace access to:

- Projects.
- Test definitions.
- Run histories.
- Screenshots and traces.
- Credentials.
- Notifications.
- Billing records.
- API keys.
- Exported reports.
- Integration tokens.

Use server-side authorization, tenant-scoped database queries, secure artifact access, and automated cross-tenant security tests.

Consider defense-in-depth measures such as PostgreSQL row-level security where appropriate, without relying on any one control as a substitute for correct authorization.

## 10.3 Secrets and external integrations

Design for:

- Encryption of sensitive credentials.
- Restricted access to decryption keys.
- Safe secret rotation.
- Least-privilege access scopes.
- Webhook-signature verification.
- Replay protection where applicable.
- Redaction in logs and artifacts.
- Revocation and deletion.
- Secure environment configuration.

## 10.4 Application and infrastructure security

Include:

- Authentication and session security.
- CSRF protection where applicable.
- Input validation.
- Secure headers and transport.
- Rate limiting and abuse prevention.
- Dependency and container scanning.
- Software composition analysis.
- Static analysis.
- Secret detection.
- Database access controls.
- Backup security.
- Artifact access control.
- Administrative audit logs.
- Resource-exhaustion protection.
- Safe logging and privacy controls.

Produce a threat register with attack scenarios, impact, likelihood, mitigations, owner, and verification criteria.

Never declare the system secure merely because an automated scanner passes.

# 11. CI/CD AND DEPLOYMENT ARCHITECTURE

Design the complete development-to-production path.

## 11.1 Environments

Define:

- Local development.
- Pull-request preview.
- Staging.
- Production.
- Optional isolated security or load-testing environment.

Specify the purpose, data policy, credentials, network access, and allowed operations of each environment.

Keep staging credentials and data separate from production.

## 11.2 Pull-request pipeline

Design a pipeline that may include:

1. Formatting and linting.
2. Type checking.
3. Python static checks.
4. Unit tests.
5. API and database integration tests.
6. Migration validation.
7. Frontend and backend builds.
8. Dependency and secret scanning.
9. Docker image build.
10. Container and software composition checks.
11. Browser test suites against an appropriate test target.
12. Artifact publication.
13. Preview or staging deployment.
14. Smoke tests.
15. Required approval gates for production changes.

Specify when each stage runs, whether it blocks merging, how failures are reported, and how flaky tests are treated.

## 11.3 Deployment release process

Plan for:

- Immutable versioned builds.
- Explicit artifact promotion.
- Backward-compatible database migrations.
- Graceful application and worker upgrades.
- Queue-payload compatibility across releases.
- Health checks.
- Post-deployment smoke tests.
- Deployment metadata.
- Release history.
- Rollback or forward-fix procedures.
- Deployment failure alerts.
- Configuration validation.

Do not assume every deployment provider supports identical rollback behavior.

Document provider-specific deployment limitations and the recovery path for the selected architecture.

## 11.4 Infrastructure

Define the expected structure for:

- Frontend hosting.
- API services.
- Browser workers.
- Queue or workflow infrastructure.
- Scheduler.
- PostgreSQL.
- Redis-compatible services if selected.
- Object storage.
- Notification providers.
- DNS and TLS.
- Secrets.
- Metrics, logs, and error tracking.

Plan infrastructure as code when useful and justified.

Keep the first deployment maintainable. Do not mandate Kubernetes unless the capacity, isolation, scheduling, or operational requirements genuinely justify it.

## 11.5 Local reproducibility

Plan Docker Compose and documented setup commands so a developer can start the required local services, run migrations, start the API and worker, execute representative checks, and run automated tests without undocumented manual steps.

Define expected development dependencies and health checks.

# 12. OBSERVABILITY, SRE, AND OPERATIONS

Release Guardian must monitor its own infrastructure independently of the websites it monitors.

Design telemetry for:

- API availability and latency.
- Database latency and connection exhaustion.
- Queue depth and age.
- Scheduler lateness.
- Job execution duration.
- Job failures and retries.
- Worker availability.
- Browser crashes.
- Artifact storage failures.
- Notification delays.
- Webhook rejection and retry rates.
- Billing or usage reconciliation failures where relevant.
- Tenant quota violations.
- AI request cost and error rate, if AI is enabled.

Use structured logs, metrics, traces, correlation IDs, and protected diagnostic evidence.

Do not log customer secrets, authentication tokens, or unnecessary personal data.

Define alert rules for the monitoring platform itself, especially missed scheduled checks and sustained queue backlogs.

## 12.1 SLOs and recovery objectives

Propose explicit service-level objectives for the API, scheduler, job execution, and notification pipeline.

Include:

- Availability measurement.
- Latency percentiles.
- Maximum acceptable scheduling delay.
- Failure-detection delay.
- Notification-delivery objectives.
- Queue backlog thresholds.
- Recovery-time objective.
- Recovery-point objective.

Treat these as proposed engineering targets that require capacity and cost validation, not guaranteed performance claims.

Document a plan for database backups, restore tests, incident simulations, deployment recovery, worker restart recovery, and queue recovery.

## 12.2 Runbooks

Define runbooks for:

- Website appears down.
- Worker pool unavailable.
- Queue backlog growing.
- Scheduler stopped.
- Database unavailable.
- Migration failed.
- Notification provider unavailable.
- False-positive incident storm.
- Suspected security breach.
- Credentials compromised.
- Storage exhausted.
- Cost spike.
- Deployment regression.
- Backup restoration.

Include detection, immediate containment, investigation, recovery, verification, and escalation.

# 13. QUALITY ENGINEERING AND TEST STRATEGY

Create a testing pyramid and testing matrix.

Include:

**Unit tests**
- Domain rules.
- Assertions.
- Job scheduling decisions.
- Retry calculations.
- Incident state transitions.
- Regression comparisons.
- Authorization policies.

**Integration tests**
- Database transactions.
- Queue publishing and consumption.
- Scheduler behavior.
- Notification adapters.
- Webhook ingestion.
- Authentication and permissions.
- Artifact storage.
- Database migrations.

**End-to-end tests**
- Account and workspace creation.
- Project registration.
- Monitor configuration.
- Test execution.
- Failure detection.
- Incident lifecycle.
- Notification delivery.
- Deployment verification.
- Workspace invitations and roles.

**Security tests**
- Cross-tenant access attempts.
- SSRF destination restrictions.
- Redirect and DNS edge cases.
- Credential redaction.
- Webhook signature validation.
- Unauthorized administrative actions.
- Artifact-access violations.

**Resilience tests**
- Worker crash and restart.
- Duplicate message delivery.
- Scheduler restart.
- Temporary network outage.
- Notification-provider failure.
- Database reconnection.
- Backlog recovery.

**Performance and capacity tests**
- Concurrent users.
- Concurrent audits.
- Burst deployment events.
- Scheduler processing time.
- Queue throughput.
- Database connection limits.
- Browser memory and CPU utilization.
- Artifact storage growth.

Define release gates using measured, reproducible criteria. Choose coverage thresholds appropriate to risk; do not optimize for coverage percentage alone.

# 14. AI QUALITY AND EVALUATION

If AI features are recommended, define:

- Supported use cases.
- Explicitly prohibited actions.
- Model-provider abstraction where useful.
- Data redaction.
- Prompt-injection threat model.
- Evidence citation format.
- Structured output schema.
- Confidence and uncertainty presentation.
- Human-review requirements.
- Evaluation dataset.
- Expected behavior on insufficient evidence.
- Model-version tracking.
- Latency and spending limits.
- Fallback behavior when providers fail.

Build a repeatable evaluation set of real or safely anonymized failure cases.

Measure whether AI explanations are supported by evidence, whether they identify the correct failed component, and whether they invent details.

Never allow AI-generated conclusions to overwrite the original test evidence or deterministic result status.

# 15. COST AND CAPACITY PLANNING

Create a transparent model of the product's resource use.

Identify the principal cost drivers:

- Hosting.
- API execution.
- Browser workers.
- Lighthouse audits.
- Database storage and compute.
- Queue operations.
- Artifact storage.
- Network egress.
- Email and messaging.
- Logs and traces.
- External monitoring regions.
- AI token consumption, if enabled.
- Billing-provider costs where applicable.

Create low, expected, and high usage scenarios based on explicit assumptions.

Model the relationship between monitored projects, environments, check frequency, pages per audit, duration, concurrency, and total worker demand.

Distinguish estimates from quoted provider pricing.

Evaluate which features need quotas, sampling, retention limits, or additional charges to prevent uncontrolled consumption.

Recommend capacity thresholds and the conditions that justify adding more workers, changing database capacity, or adopting a more sophisticated orchestration system.

# 16. PROJECT STRUCTURE AND ENGINEERING TOOLCHAIN

Recommend a repository layout appropriate to the selected architecture.

Evaluate a structure similar to:

```text
release-guardian/
├── apps/
│   └── web/
├── services/
│   ├── api/
│   ├── worker/
│   └── scheduler/
├── packages/
│   └── api-contracts/
├── tests/
│   ├── integration/
│   ├── security/
│   ├── e2e/
│   └── load/
├── infra/
│   ├── docker/
│   ├── deployment/
│   └── scripts/
├── docs/
│   ├── architecture/
│   ├── operations/
│   ├── security/
│   └── master-plan/
├── docker-compose.yml
├── .github/
│   └── workflows/
├── .env.example
├── AGENTS.md
└── README.md
```

This is a proposed structure, not a mandate to introduce every directory or service.

Explain which components belong in one deployable unit, which need separate containers, and which should remain modules rather than independent services.

Evaluate the complete toolchain:

- Runtime and version management.
- Package managers and lockfile policy.
- Formatting and linting.
- Static type checking.
- Database migrations.
- API schema generation.
- Unit and integration tests.
- Browser test tooling.
- Container builds.
- Dependency updates.
- Security checks.
- CI/CD.
- Local development.
- Code review.
- Documentation.
- Release tagging.
- Monitoring and support.

Use supported versions after checking current official documentation. Avoid unverified version pins or invented compatibility claims.

# 17. DOCUMENTATION DELIVERABLES

Create the master plan as organized, maintainable documentation.

Preferred destination:

`docs/master-plan/release-guardian/`

Before creating anything, check for existing documents that already serve these purposes. Preserve useful existing material and cross-reference it rather than creating contradictory copies.

Plan and, where permitted, produce:

1. `00-MASTER-PLAN.md` — executive overview, goals, scope, recommended architecture, phases, dependencies, and approval gates.
2. `01-PRODUCT-REQUIREMENTS.md` — personas, use cases, functional requirements, non-functional requirements, and product boundaries.
3. `02-FEATURE-CATALOG.md` — complete feature inventory, priority, dependencies, acceptance criteria, and phase assignments.
4. `03-TECHNOLOGY-DECISIONS.md` — candidate stacks, decision matrix, technology selection, trade-offs, and confidence.
5. `04-SYSTEM-ARCHITECTURE.md` — system context, containers, components, deployment topology, and architecture diagrams.
6. `05-DATA-MODEL.md` — entity relationships, indexes, ownership, lifecycle, migrations, and retention.
7. `06-API-AND-EVENT-CONTRACTS.md` — endpoint families, authorization, event definitions, idempotency, versioning, and error handling.
8. `07-QUEUE-SCHEDULER-AND-WORKERS.md` — scheduling, dispatch, execution semantics, retries, concurrency, isolation, and recovery.
9. `08-SECURITY-AND-THREAT-MODEL.md` — threats, mitigations, SSRF design, tenant isolation, secrets, and security verification.
10. `09-TEST-AND-QUALITY-STRATEGY.md` — test architecture, coverage policy, test data, CI gates, resilience tests, and release criteria.
11. `10-DEPLOYMENT-AND-CICD.md` — local development, preview, staging, production, containers, pipelines, migrations, deployment, and rollback.
12. `11-OBSERVABILITY-AND-OPERATIONS.md` — SLO proposals, telemetry, alerts, runbooks, incident response, backups, and disaster recovery.
13. `12-AI-ENGINEERING-AND-EVALUATION.md` — optional AI use cases, evidence rules, model security, evaluations, privacy, and spending controls.
14. `13-COST-AND-CAPACITY-MODEL.md` — resource estimates, demand scenarios, capacity planning, quotas, and cost risks.
15. `14-IMPLEMENTATION-ROADMAP.md` — ordered milestones, dependencies, acceptance criteria, and verification gates.
16. `15-RISK-REGISTER.md` — ranked risks, likelihood, impact, mitigations, owners, and residual risk.
17. `16-OPEN-DECISIONS.md` — unresolved choices, alternatives, recommended resolutions, and owner approvals.
18. `17-SOURCE-REGISTER.md` — authoritative documentation, verified product claims, compatibility references, and research dates.

Adjust the document set if an existing repository already has an equivalent organizational structure.

Avoid duplicating the same long explanation across numerous files. Use the master plan as the index and link to supporting documents.

Use architecture diagrams where they add clarity. Include:

- System context diagram.
- Logical component diagram.
- Deployment diagram.
- Core data model.
- Job execution sequence.
- Deployment verification sequence.
- Incident lifecycle.
- CI/CD pipeline.
- Threat-boundary diagram.

Keep diagrams consistent with the text and the chosen architecture.

# 18. IMPLEMENTATION ROADMAP DESIGN

Construct an ordered roadmap for the complete product.

The roadmap must cover all approved capabilities; phase ordering is not permission to drop features.

At minimum, evaluate these phases:

**Phase A — Discovery and decisions**
- Repository and environment audit.
- Product requirements.
- Market and integration research.
- Architecture and deployment decisions.
- Risk and threat analysis.

**Phase B — Engineering foundation**
- Repository structure.
- Development tooling.
- Local containers.
- Configuration conventions.
- CI baseline.
- Logging and testing foundations.

**Phase C — Identity and workspace model**
- Authentication.
- Workspaces and memberships.
- Project and environment structure.
- Permission enforcement.
- Audit logging.

**Phase D — Durable execution platform**
- Job model.
- Queue and scheduler.
- Worker lifecycle.
- Retries and idempotency.
- Execution tracking.
- Operational telemetry.

**Phase E — Monitoring and audit engine**
- Uptime and HTTP checks.
- Endpoint policies.
- Browser test execution.
- Evidence storage.
- Performance and technical SEO audits.
- Scheduling and history.

**Phase F — Release verification**
- Deployment integrations.
- Release-triggered suites.
- Baselines.
- Regression detection.
- CI checks.
- Deployment-to-incident correlation.

**Phase G — Incident management**
- Alert rules.
- Incident lifecycle.
- Notification providers.
- Escalation.
- Maintenance windows.
- Diagnostic reports.

**Phase H — Complete product experience**
- Project dashboards.
- Test builder.
- Historical reports.
- Team collaboration.
- Public API and CLI.
- Documentation and onboarding.

**Phase I — Advanced capabilities**
- Optional AI-assisted diagnostics.
- Test generation assistance.
- Advanced analytics.
- Extended integrations.
- Usage metering and billing.
- Additional monitoring regions, where justified.

**Phase J — Production readiness**
- Security validation.
- Load and resilience testing.
- Backup restoration.
- Deployment drills.
- Observability review.
- Operational runbooks.
- Cost validation.
- Launch readiness review.

Reorder these phases if dependencies or the existing codebase require it. Explain the reason for major ordering changes.

For each phase, provide:

- Objective.
- Scope.
- Prerequisites.
- Deliverables.
- Architecture impact.
- Database changes.
- Security requirements.
- Testing requirements.
- Deployment implications.
- Measurable acceptance criteria.
- Exit gate.
- Main risks.

Estimate effort in relative units such as S, M, L, or XL unless sufficient evidence exists for a credible time estimate.

Identify the critical path, parallelizable work, and tasks that require the owner's approval.

# 19. ENGINEERING DECISION RECORDS

Record important decisions in an architecture-decision format.

Each record should contain:

- Decision title and identifier.
- Status.
- Context.
- Requirements.
- Options considered.
- Evaluation criteria.
- Chosen option.
- Reasons for selection.
- Rejected alternatives and why.
- Consequences.
- Operational and security implications.
- Migration or replacement strategy.
- Sources.
- Revisit conditions.

At minimum, evaluate decisions about:

- Monorepo versus multiple repositories.
- Frontend and backend framework boundaries.
- Authentication.
- Queue and workflow engine.
- Scheduling.
- Browser-worker isolation.
- Database and tenant isolation.
- Object storage and artifact retention.
- Deployment topology.
- Observability stack.
- Billing integration.
- AI provider strategy.
- Infrastructure as code.
- Rollback strategy.

Do not finalize controversial choices without explaining the trade-offs.

# 20. RESEARCH QUALITY AND MARKET VALIDATION

Before claiming Release Guardian has a competitive advantage:

1. Identify relevant existing products.
2. Verify their current capabilities from reliable public sources.
3. Compare monitoring, browser testing, deployment integration, incident handling, and diagnostics.
4. Distinguish capabilities confirmed by documentation from marketing claims or assumptions.
5. Identify product gaps worth investigating.
6. Recommend a measurable differentiation strategy.

Do not recommend copying a competitor's feature list as the complete product strategy.

Explain which problems are broadly solved, which are poorly integrated for the target audience, and which claims still require customer interviews or experiments.

# 21. DEFINITION OF PRODUCTION-READY

Define an explicit production-readiness checklist.

The final system must have a credible plan for:

- Correct authentication and authorization.
- Multi-tenant isolation.
- Secure target URL handling.
- Safe browser execution.
- Reproducible builds.
- Version-controlled configuration.
- Automated tests.
- Database migrations.
- Queue recovery.
- Duplicate-job handling.
- Controlled concurrency.
- Error reporting.
- Health checks.
- Scheduler monitoring.
- Incident management.
- Backup and restore verification.
- Deployment rollback or forward recovery.
- Secret rotation.
- Dependency security.
- Cost controls.
- Data retention and deletion.
- User documentation.
- Operator runbooks.
- Incident response.
- Tested disaster recovery.

Do not report production readiness because a dashboard renders or a deployment succeeds. Readiness requires evidence against explicit acceptance criteria.

# 22. MANDATORY FINAL QUALITY REVIEW

Before presenting the plan, perform an independent review from each critical perspective:

**Architecture review**
- Are system boundaries coherent?
- Are the right components separate?
- Is anything unnecessarily distributed?

**Automation review**
- Can scheduled and event-triggered jobs recover from failures?
- Are job outcomes reproducible and auditable?

**Security review**
- Can one workspace access another workspace's data?
- Can a monitored website reach internal infrastructure?
- Are arbitrary scripts prevented from escaping their intended sandbox?

**Data review**
- Are transactions, idempotency, migrations, and retention addressed?

**Operations review**
- Can an operator determine whether a failure is in the monitored website or in Release Guardian itself?

**Deployment review**
- Can a release fail safely?
- Can a previous version recover without losing queued jobs or corrupting data?

**Product review**
- Does the platform solve a genuine operational problem?
- Is its differentiation credible?
- Are AI and other advanced features worth their complexity?

**Cost review**
- Does the architecture support reasonable usage growth?
- Are expensive operations metered and controlled?

**Documentation review**
- Are the diagrams, API model, data model, feature catalog, and roadmap internally consistent?
- Are dependencies and unresolved decisions explicit?

Resolve contradictions before presenting the final recommendation.

# 23. COMPLETION CRITERIA FOR THIS ENGAGEMENT

This engagement is complete when:

1. The repository baseline and operating constraints are recorded.
2. The product's purpose and boundaries are clearly defined.
3. The complete feature catalog has been evaluated.
4. At least three architecture and deployment approaches have been compared.
5. A recommended stack and deployment topology are justified.
6. The data model and API boundaries are specified.
7. Scheduling, queues, workers, and browser isolation are designed.
8. Security threats and mitigations are documented.
9. Testing and quality gates are defined.
10. CI/CD, environment management, deployment, and recovery are planned.
11. Observability and operational responsibilities are specified.
12. AI use cases have explicit safety and evaluation requirements.
13. Cost and capacity drivers are identified.
14. The complete implementation roadmap includes all approved product capabilities.
15. Decisions requiring owner approval are listed.
16. Source references are relevant and verifiable.
17. Planning documents are written only where authorized.
18. No application implementation or deployment has been performed.

# 24. REQUIRED FINAL RESPONSE

When you finish, provide a structured report containing:

**A. Executive summary**
- What Release Guardian is.
- The operational problem it solves.
- Who uses it.
- The recommended product direction.

**B. Repository assessment**
- What actually exists.
- What was verified.
- What remains unknown.
- Existing changes preserved.

**C. Architecture recommendation**
- Recommended stack.
- Logical system diagram.
- Deployment topology.
- Justification and alternatives.

**D. Feature and capability coverage**
- Complete product modules.
- Important dependencies.
- Major risks.

**E. Implementation roadmap**
- Ordered phases.
- Milestones.
- Acceptance criteria.
- Critical path.

**F. Security and production readiness**
- Principal threats.
- Mitigation strategy.
- Operational and release gates.

**G. Economics and scalability**
- Main cost drivers.
- Capacity assumptions.
- Scaling path.

**H. Owner decisions**
- Decisions genuinely requiring approval.
- Recommended defaults.
- Consequences of each option.

**I. Documentation deliverables**
- Exact paths created or proposed.
- Brief contents of each document.
- Explicit distinction between created files and content only shown in the response.

**J. Final status**
- Planning completed or partially completed.
- Research limitations.
- Unresolved questions.
- Confirmation that application code and infrastructure were not modified.

Do not claim completion of an activity that was not performed.

---

# EXECUTION INSTRUCTION

Begin with repository discovery and evidence collection.

Then research the current official documentation, establish the real constraints, compare architectural options, and produce the integrated master plan.

Use principal-level engineering judgment to recommend a coherent, secure, maintainable, and scalable system. Make assumptions explicit, document alternatives, and challenge unnecessary complexity.

Do not begin application implementation. Do not deploy anything.

**The goal of this engagement is to finish with a complete blueprint that an engineering team can execute in controlled, testable phases without having to rediscover the architecture, requirements, tooling, security model, or deployment strategy.**