from tests.conftest import auth_headers, register


def _setup(client):
    token = register(client)["access_token"]
    headers = auth_headers(token)
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    return headers, workspace


def _create_key(client, headers, workspace_id, scopes):
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/api-keys",
        headers=headers,
        json={"name": "ci", "scopes": scopes},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _key_headers(raw):
    return {"Authorization": f"Bearer {raw}"}


def test_read_key_lists_resources_but_cannot_write(client):
    headers, workspace = _setup(client)
    created = _create_key(client, headers, workspace["id"], [])
    key_headers = _key_headers(created["key"])

    listed = client.get(f"/api/v1/projects?workspace_id={workspace['id']}", headers=key_headers)
    assert listed.status_code == 200
    assert listed.json() == []

    denied = client.post(
        "/api/v1/projects",
        headers=key_headers,
        json={"workspace_id": workspace["id"], "name": "Blocked"},
    )
    assert denied.status_code == 403


def test_write_key_can_create_project(client):
    headers, workspace = _setup(client)
    created = _create_key(client, headers, workspace["id"], ["write"])
    key_headers = _key_headers(created["key"])

    response = client.post(
        "/api/v1/projects",
        headers=key_headers,
        json={"workspace_id": workspace["id"], "name": "From CI"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "From CI"


def test_key_is_bound_to_its_workspace(client):
    headers, workspace = _setup(client)
    other = client.post("/api/v1/workspaces", headers=headers, json={"name": "Other"}).json()
    created = _create_key(client, headers, workspace["id"], ["write"])

    response = client.get(
        f"/api/v1/projects?workspace_id={other['id']}", headers=_key_headers(created["key"])
    )
    assert response.status_code == 404


def test_revoked_and_unknown_keys_are_rejected(client):
    headers, workspace = _setup(client)
    created = _create_key(client, headers, workspace["id"], ["write"])

    revoked = client.delete(f"/api/v1/api-keys/{created['id']}", headers=headers)
    assert revoked.status_code == 204

    after = client.get(
        f"/api/v1/projects?workspace_id={workspace['id']}",
        headers=_key_headers(created["key"]),
    )
    assert after.status_code == 401

    unknown = client.get(
        f"/api/v1/projects?workspace_id={workspace['id']}",
        headers=_key_headers("rg_not-a-real-key"),
    )
    assert unknown.status_code == 401
