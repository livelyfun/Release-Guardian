import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["WORKER_MODE"] = "inline"
os.environ["JWT_SECRET"] = "test-secret-0123456789abcdef0123456789"
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOW_PRIVATE_URLS"] = "false"
os.environ["RATE_LIMIT_AUTH_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_API_PER_MINUTE"] = "10000"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def register(client: TestClient, email: str = "owner@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "name": "Owner"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
