from tests.conftest import auth_headers, register


def _workspace(client, token):
    headers = auth_headers(token)
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    return headers, workspace


def test_create_list_update_delete_webhook_channel(client):
    token = register(client)["access_token"]
    headers, workspace = _workspace(client, token)

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/notification-channels",
        headers=headers,
        json={"kind": "webhook", "config": {"url": "https://hooks.example.com/rg"}},
    )
    assert response.status_code == 201, response.text
    channel = response.json()
    assert channel["kind"] == "webhook"
    assert channel["enabled"] is True

    listed = client.get(
        f"/api/v1/workspaces/{workspace['id']}/notification-channels", headers=headers
    ).json()
    assert [item["id"] for item in listed] == [channel["id"]]

    updated = client.patch(
        f"/api/v1/notification-channels/{channel['id']}",
        headers=headers,
        json={"enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False

    attempts = client.get(
        f"/api/v1/notification-channels/{channel['id']}/attempts", headers=headers
    )
    assert attempts.status_code == 200
    assert attempts.json() == []

    deleted = client.delete(
        f"/api/v1/notification-channels/{channel['id']}", headers=headers
    )
    assert deleted.status_code == 204
    assert client.get(
        f"/api/v1/workspaces/{workspace['id']}/notification-channels", headers=headers
    ).json() == []


def test_channel_config_validation(client):
    token = register(client)["access_token"]
    headers, workspace = _workspace(client, token)
    url = f"/api/v1/workspaces/{workspace['id']}/notification-channels"

    missing_url = client.post(
        url, headers=headers, json={"kind": "webhook", "config": {}}
    )
    assert missing_url.status_code == 422

    bad_scheme = client.post(
        url, headers=headers, json={"kind": "webhook", "config": {"url": "ftp://x"}}
    )
    assert bad_scheme.status_code == 422


def test_viewer_cannot_manage_channels(client):
    owner = register(client)["access_token"]
    viewer = register(client, email="viewer@example.com")["access_token"]
    headers, workspace = _workspace(client, owner)

    added = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        headers=headers,
        json={"email": "viewer@example.com", "role": "viewer"},
    )
    assert added.status_code == 201, added.text

    viewer_headers = auth_headers(viewer)
    listed = client.get(
        f"/api/v1/workspaces/{workspace['id']}/notification-channels",
        headers=viewer_headers,
    )
    assert listed.status_code == 200

    denied = client.post(
        f"/api/v1/workspaces/{workspace['id']}/notification-channels",
        headers=viewer_headers,
        json={"kind": "webhook", "config": {"url": "https://hooks.example.com/rg"}},
    )
    assert denied.status_code == 403
