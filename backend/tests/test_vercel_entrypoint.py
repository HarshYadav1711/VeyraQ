"""Vercel entrypoint exposes the same FastAPI application instance."""

from fastapi.testclient import TestClient

from api.index import app as entry_app
from app.main import app as main_app


def test_vercel_entrypoint_reexports_main_app() -> None:
    assert entry_app is main_app
    client = TestClient(entry_app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
