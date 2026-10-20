## What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## Why

<!-- The problem being solved, not just the implementation. -->

## How to verify

<!-- Commands you ran, or steps a reviewer can follow. -->

## Checklist

- [ ] `make lint`, `make test`, and `make check` pass locally
- [ ] New or changed behaviour has tests
- [ ] Tenant-scoped queries go through `api/v1/deps.py` / `api/v1/access.py`
- [ ] New outbound URL fetches go through `services/url_guard.py`
- [ ] `.env.example` and the relevant doc are updated if configuration changed
- [ ] No secrets, database files, or build output are included
- [ ] This pull request does not contain a security fix (those follow SECURITY.md)
