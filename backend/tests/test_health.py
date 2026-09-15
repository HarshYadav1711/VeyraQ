from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "veyraq-api"}


def test_readiness_success_when_database_connected(client: TestClient) -> None:
    with patch("app.api.routes.health.check_database_connection", return_value=True):
        response = client.get("/api/v1/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def test_readiness_failure_returns_503_without_secrets(client: TestClient) -> None:
    with patch("app.api.routes.health.check_database_connection", return_value=False):
        response = client.get("/api/v1/readiness")

    assert response.status_code == 503
    body = response.json()
    assert body == {"status": "unavailable", "database": "disconnected"}

    serialized = response.text.lower()
    assert "postgres:postgres" not in serialized
    assert "password" not in serialized
    assert "traceback" not in serialized
    assert "postgresql+psycopg://" not in serialized
