# Contributing to Release Guardian

Thanks for taking the time to contribute. This project is early and moving
quickly; small, focused pull requests are much easier to review than large ones.

## Before you start

- For anything larger than a bug fix, open an issue first and describe the
  problem and your proposed approach. It avoids building something that will not
  be merged.
- For security issues, follow [SECURITY.md](SECURITY.md). Never open a public
  issue for a vulnerability.
- By contributing, you agree that your contributions are licensed under the
  project's [AGPL-3.0-or-later](LICENSE) license. There is no CLA to sign.

## Development setup

Requirements: Python 3.11+ (CI uses 3.12), Node.js 20+, PostgreSQL 16 and Redis
(Docker Compose is the simplest way to get both), and optionally Docker.

```bash
cp .env.example .env
make install        # backend + frontend dependencies
make up             # Postgres and Redis via Docker Compose
make migrate        # apply Alembic migrations
make dev-api        # API on http://localhost:8000
make dev-worker     # Celery worker
make dev-web        # dashboard on http://localhost:3000
```

The backend virtualenv used in CI and by the Makefile is `backend/.venv`.

## Checks to run before opening a pull request

```bash
make lint     # ruff (backend) + ESLint/tsc (frontend)
make test     # backend pytest suite
make check    # lint + tests + frontend build
```

If you touched the browser worker or Playwright flows, note in the pull request
whether you ran a browser check locally. Playwright browsers and the Lighthouse
CLI are not installed by default; the CI job for the frontend does not exercise
them.

## Style

- Python: Ruff with `E,F,I,B,UP` (line length 100). Follow the existing layout in
  `backend/app` — routers in `api/v1/endpoints`, business logic in `services`,
  Celery tasks in `workers/tasks`.
- TypeScript: strict mode. Path alias `@/*` maps to `frontend/src/*`.
- Keep tenant scoping server-side. Any new query that touches workspace-owned
  data must go through `api/v1/deps.py` and `api/v1/access.py`.
- Any new outbound URL fetch must pass through `services/url_guard.py`.
- Errors must use the structured envelope in `core/errors.py`.

## Commits and pull requests

- Keep commits coherent and write messages in the imperative mood
  ("Add artifact retention", not "Added").
- Describe *why* in the pull request body, not just *what*. Mention behaviour
  changes, migration steps, and anything a reviewer should look at first.
- Add or update tests for behaviour changes. Bug fixes should include a test
  that fails without the change.
- Do not include generated artifacts, database files, or build output.
- CI must be green before merge.

## Adding a dependency

Prefer the standard library and what is already installed. If you add a
dependency, explain why in the pull request and make sure its license is
compatible with AGPL-3.0.

## Documentation

Documentation lives in `docs/`. `docs/master-plan/` is the design record;
`docs/operations/` is the runbook set. If you change configuration variables,
update `.env.example` and the relevant operations doc in the same pull request.
