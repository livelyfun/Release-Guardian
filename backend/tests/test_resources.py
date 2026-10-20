from tests.conftest import auth_headers, register


def _setup_project(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"workspace_id": workspace["id"], "name": "Marketing Site"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    environment = client.post(
        f"/api/v1/projects/{project_id}/environments",
        headers=headers,
        json={"name": "production", "base_url": "https://example.com", "is_production": True},
    )
    assert environment.status_code == 201, environment.text
    environment_id = environment.json()["id"]

    monitor = client.post(
        f"/api/v1/environments/{environment_id}/monitors",
        headers=headers,
        json={"name": "Homepage", "kind": "http", "target_url": "https://example.com"},
    )
    assert monitor.status_code == 201, monitor.text
    return headers, workspace, project_id, environment_id, monitor.json()


def test_project_environment_monitor_flow(client):
    headers, workspace, project_id, environment_id, monitor = _setup_project(client)

    projects = client.get(
        f"/api/v1/projects?workspace_id={workspace['id']}", headers=headers
    ).json()
    assert len(projects) == 1

    environments = client.get(f"/api/v1/projects/{project_id}/environments", headers=headers).json()
    assert environments[0]["name"] == "production"

    monitors = client.get(
        f"/api/v1/environments/{environment_id}/monitors", headers=headers
    ).json()
    assert monitors[0]["target_url"] == "https://example.com"
    assert monitors[0]["id"] == monitor["id"]


def test_tenant_isolation_between_users(client):
    headers_a, workspace_a, _, _, _ = _setup_project(client)

    register(client, email="other@example.com")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "supersecret123"},
    )
    headers_b = auth_headers(login.json()["access_token"])

    visible = client.get("/api/v1/workspaces", headers=headers_b).json()
    assert workspace_a["id"] not in [workspace["id"] for workspace in visible]

    forbidden = client.get(
        f"/api/v1/projects?workspace_id={workspace_a['id']}", headers=headers_b
    )
    assert forbidden.status_code == 404


def test_scoped_lists_by_workspace(client):
    headers, workspace, _, _, monitor = _setup_project(client)

    monitors = client.get(
        f"/api/v1/monitors?workspace_id={workspace['id']}", headers=headers
    ).json()
    assert len(monitors) == 1
    assert monitors[0]["id"] == monitor["id"]

    runs = client.get(f"/api/v1/runs?workspace_id={workspace['id']}", headers=headers).json()
    assert runs == []


def test_api_key_lifecycle(client):
    headers, workspace, _, _, _ = _setup_project(client)
    created = client.post(
        f"/api/v1/workspaces/{workspace['id']}/api-keys",
        headers=headers,
        json={"name": "CI"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["key"].startswith("rg_")
    assert body["prefix"]

    listed = client.get(
        f"/api/v1/workspaces/{workspace['id']}/api-keys", headers=headers
    ).json()
    assert len(listed) == 1

    revoked = client.delete(f"/api/v1/api-keys/{body['id']}", headers=headers)
    assert revoked.status_code == 204

    listed_after = client.get(
        f"/api/v1/workspaces/{workspace['id']}/api-keys", headers=headers
    ).json()
    assert listed_after[0]["revoked_at"] is not None


def test_audit_log_records_project_creation(client):
    headers, workspace, _, _, _ = _setup_project(client)
    logs = client.get(
        f"/api/v1/workspaces/{workspace['id']}/audit-logs", headers=headers
    ).json()
    actions = {entry["action"] for entry in logs}
    assert "project.create" in actions
    assert "monitor.create" in actions


def test_invalid_target_url_rejected(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"workspace_id": workspace["id"], "name": "Bad"},
    ).json()
    environment = client.post(
        f"/api/v1/projects/{project['id']}/environments",
        headers=headers,
        json={"name": "prod", "base_url": "example.com", "is_production": False},
    )
    assert environment.status_code == 422


def test_member_invite_requires_known_user(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        headers=headers,
        json={"email": "nobody@example.com", "role": "viewer"},
    )
    assert response.status_code == 404


def test_team_member_role_updates_and_removal(client):
    owner_headers = auth_headers(register(client)["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=owner_headers).json()[0]
    members_url = f"/api/v1/workspaces/{workspace['id']}/members"

    register(client, email="developer@example.com")
    added = client.post(
        members_url,
        headers=owner_headers,
        json={"email": "developer@example.com", "role": "viewer"},
    )
    assert added.status_code == 201, added.text
    assert added.json()["email"] == "developer@example.com"
    assert added.json()["name"] == "Owner"
    membership_id = added.json()["id"]

    promoted = client.patch(
        f"{members_url}/{membership_id}",
        headers=owner_headers,
        json={"role": "developer"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "developer"

    members = client.get(members_url, headers=owner_headers).json()
    owner_membership = next(member for member in members if member["role"] == "owner")
    last_owner = client.patch(
        f"{members_url}/{owner_membership['id']}",
        headers=owner_headers,
        json={"role": "admin"},
    )
    assert last_owner.status_code == 409

    # A non-owner admin cannot touch owner membership.
    admin_headers = auth_headers(register(client, email="admin@example.com")["access_token"])
    client.post(
        members_url,
        headers=owner_headers,
        json={"email": "admin@example.com", "role": "admin"},
    )
    grant_owner = client.patch(
        f"{members_url}/{membership_id}",
        headers=admin_headers,
        json={"role": "owner"},
    )
    assert grant_owner.status_code == 403
    remove_owner = client.delete(
        f"{members_url}/{owner_membership['id']}", headers=admin_headers
    )
    assert remove_owner.status_code == 403

    removed = client.delete(f"{members_url}/{membership_id}", headers=owner_headers)
    assert removed.status_code == 204
    remaining = client.get(members_url, headers=owner_headers).json()
    assert [member["email"] for member in remaining] == [
        "owner@example.com",
        "admin@example.com",
    ]
