"""Outbound GitHub commit statuses for deployment verification."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import utcnow
from app.models.project import Environment, Project
from app.models.release import Deployment

GITHUB_STATE = {
    "pending": "pending",
    "passed": "success",
    "failed": "failure",
    "inconclusive": "error",
}


def parse_github_repo(repository_url: str | None) -> tuple[str, str] | None:
    if not repository_url:
        return None
    value = repository_url.strip()
    if value.startswith("git@github.com:"):
        path = value.split(":", 1)[1]
    else:
        parsed = urlparse(value)
        if parsed.hostname not in {"github.com", "www.github.com"}:
            return None
        path = parsed.path
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    parts = path.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def deployment_state(status: str) -> str:
    return GITHUB_STATE.get(status, "pending")


def post_deployment_status(db: Session, deployment: Deployment) -> dict:
    """Post (or skip) a commit status, updating deployment meta. Never raises."""
    token = settings.github_status_token
    if not token:
        return {"posted": False, "reason": "not_configured"}

    environment = db.get(Environment, deployment.environment_id)
    project = db.get(Project, environment.project_id) if environment else None
    repo = parse_github_repo(project.repository_url if project else None)
    if repo is None:
        return {"posted": False, "reason": "unsupported_repository"}

    state = deployment_state(deployment.status)
    meta = dict(deployment.meta or {})
    if meta.get("github_status") == state:
        return {"posted": False, "reason": "unchanged", "state": state}

    owner, name = repo
    body = {
        "state": state,
        "context": settings.github_status_context,
        "description": f"Release verification {deployment.status}"[:140],
    }
    if settings.github_status_target_url:
        body["target_url"] = settings.github_status_target_url

    request = urllib.request.Request(
        f"{settings.github_api_url.rstrip('/')}/repos/{owner}/{name}/statuses/{deployment.commit_sha}",
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        meta["github_status_error"] = str(exc)[:300]
        deployment.meta = meta
        return {"posted": False, "reason": "request_failed", "error": str(exc)[:300]}

    meta["github_status"] = state
    meta.pop("github_status_error", None)
    meta["github_status_updated_at"] = utcnow().isoformat()
    deployment.meta = meta
    return {"posted": True, "state": state}
