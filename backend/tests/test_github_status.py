import json

from app.core.config import settings
from app.models.release import Deployment
from app.services import github_status
from tests.conftest import auth_headers, register


def test_parse_github_repo_supports_https_and_ssh():
    assert github_status.parse_github_repo("https://github.com/acme/site") == ("acme", "site")
    assert github_status.parse_github_repo("https://github.com/acme/site.git") == ("acme", "site")
    assert github_status.parse_github_repo("git@github.com:acme/site.git") == ("acme", "site")
    assert github_status.parse_github_repo("https://gitlab.com/acme/site") is None
    assert github_status.parse_github_repo(None) is None


def test_post_deployment_status_updates_github_and_meta(client, db, monkeypatch):
    headers = auth_headers(register(client)["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "workspace_id": workspace["id"],
            "name": "Site",
            "repository_url": "https://github.com/acme/site",
        },
    ).json()
    environment = client.post(
        f"/api/v1/projects/{project['id']}/environments",
        headers=headers,
        json={"name": "production", "base_url": "https://example.com"},
    ).json()
    deployment = client.post(
        f"/api/v1/environments/{environment['id']}/deployments",
        headers=headers,
        json={"commit_sha": "abc1234567", "status": "success"},
    ).json()

    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout=None):
        requests.append(request)
        return FakeResponse()

    monkeypatch.setattr(github_status.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(settings, "github_status_token", "github-token")

    stored = db.get(Deployment, deployment["id"])
    assert stored is not None
    stored.status = "pending"

    first = github_status.post_deployment_status(db, stored)
    assert first["posted"] is True
    assert first["state"] == "pending"
    assert requests[0].full_url == (
        "https://api.github.com/repos/acme/site/statuses/abc1234567"
    )
    assert json.loads(requests[0].data)["state"] == "pending"
    assert stored.meta["github_status"] == "pending"

    stored.status = "failed"
    second = github_status.post_deployment_status(db, stored)
    assert second == {"posted": True, "state": "failure"}
    assert json.loads(requests[1].data)["state"] == "failure"

    third = github_status.post_deployment_status(db, stored)
    assert third["posted"] is False
    assert third["reason"] == "unchanged"
    assert len(requests) == 2
