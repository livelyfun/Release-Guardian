from tests.conftest import auth_headers, register


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_login_and_me(client):
    payload = register(client)
    assert payload["user"]["email"] == "owner@example.com"
    assert payload["access_token"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "supersecret123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"


def test_duplicate_email_conflicts(client):
    register(client)
    again = client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "supersecret123", "name": "Owner"},
    )
    assert again.status_code == 409


def test_login_rejects_bad_password(client):
    register(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_token_flow(client):
    payload = register(client)
    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
