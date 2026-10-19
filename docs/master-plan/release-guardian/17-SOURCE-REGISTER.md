# 17 — SOURCE REGISTER

**Project:** Release Guardian
**Research date:** 2026-10-19

Official references used or intended for validation. Listing a source does not imply that every
claim in the plan was re-verified during the current session. Verify versions and behavior against
the current documentation before making production commitments.

## Platform and Framework

| Topic | Source |
|---|---|
| FastAPI | https://fastapi.tiangolo.com/ |
| Starlette | https://www.starlette.io/ |
| Pydantic | https://docs.pydantic.dev/ |
| SQLAlchemy | https://docs.sqlalchemy.org/ |
| Alembic | https://alembic.sqlalchemy.org/ |
| Celery | https://docs.celeryq.dev/ |
| Redis | https://redis.io/docs/latest/ |
| PostgreSQL | https://www.postgresql.org/docs/ |
| Next.js | https://nextjs.org/docs |
| React | https://react.dev/ |
| TypeScript | https://www.typescriptlang.org/docs/ |
| Tailwind CSS | https://tailwindcss.com/docs |

## Browser, Performance, and Quality

| Topic | Source |
|---|---|
| Playwright | https://playwright.dev/docs/intro |
| Playwright Docker | https://playwright.dev/docs/docker |
| Playwright CI | https://playwright.dev/docs/ci |
| Lighthouse | https://developer.chrome.com/docs/lighthouse/ |
| Web Vitals | https://web.dev/articles/vitals |
| axe-core accessibility | https://www.deque.com/axe/ |
| OWASP ASVS | https://owasp.org/www-project-application-security-verification-standard/ |

## Security

| Topic | Source |
|---|---|
| OWASP SSRF prevention | https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html |
| OWASP Top 10 | https://owasp.org/www-project-top-ten/ |
| JWT best practices (RFC 8725) | https://www.rfc-editor.org/rfc/rfc8725 |
| Docker security | https://docs.docker.com/engine/security/ |
| GitHub Actions hardening | https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments |
| GitHub webhooks | https://docs.github.com/en/webhooks |

## Delivery and Operations

| Topic | Source |
|---|---|
| GitHub Actions | https://docs.github.com/en/actions |
| Vercel | https://vercel.com/docs |
| Neon Postgres | https://neon.tech/docs |
| Temporal | https://docs.temporal.io/ |
| OpenTelemetry | https://opentelemetry.io/docs/ |
| Prometheus alerting | https://prometheus.io/docs/alerting/latest/overview/ |

## AI (optional, deferred)

| Topic | Source |
|---|---|
| OWASP LLM Top 10 | https://owasp.org/www-project-top-10-for-large-language-model-applications/ |
| NIST AI RMF | https://www.nist.gov/itl/ai-risk-management-framework |

## Verified in This Repository

- Backend lint and tests: `backend/.venv/bin/ruff check app tests`, `backend/.venv/bin/pytest -q`.
- Frontend lint, typecheck, and build: `npm run lint`, `npx tsc --noEmit`, `npm run build`.
- Alembic initial migration upgrade and downgrade against SQLite.
- These checks were run locally against synthetic data; no production provider was contacted.
