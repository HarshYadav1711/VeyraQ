from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.routes.assistant import get_ai_service
from app.domain.complaint import ASSISTANT_MESSAGE_MAX_LENGTH, ComplaintFields
from app.main import app
from tests.fakes.ai_service import FakeAIService, empty_source_extraction, extracted_fact
from tests.test_complaint_graph import advisory_risk


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def empty_fields() -> dict:
    return ComplaintFields().model_dump(mode="json")


def test_blank_assistant_message_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/assistant/process",
        json={"message": "   ", "fields": empty_fields()},
    )
    assert response.status_code == 422


def test_ai_service_error_returns_safe_503(client: TestClient) -> None:
    service = FakeAIService(unavailable=True)
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/process",
        json={
            "message": "Apollo Pharmacy reported discolored Amoxicillin Capsules.",
            "fields": empty_fields(),
        },
    )
    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == (
        "AI processing is temporarily unavailable. Your complaint draft has not been changed."
    )
    serialized = response.text.lower()
    assert "traceback" not in serialized
    assert "groq" not in serialized
    assert "api_key" not in serialized
    assert "amoxicillin" not in serialized


def test_missing_groq_key_does_not_prevent_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_assistant_process_success_with_fake_service(client: TestClient) -> None:
    service = FakeAIService(
        source=empty_source_extraction(
            customer_name=extracted_fact("Apollo Pharmacy", "Apollo Pharmacy"),
            product_name=extracted_fact("Amoxicillin Capsules", "Amoxicillin Capsules"),
        ),
        risk=advisory_risk(),
    )
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/process",
        json={
            "message": (
                "Apollo Pharmacy reported discolored Amoxicillin Capsules "
                "500 mg from batch AMX240602."
            ),
            "fields": empty_fields(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "new_complaint"
    assert body["status"] == "needs_information"
    assert "batch_lot_number" in body["missing_required_fields"]
    assert body["patch"]["changes"]["product_name"]["provenance"] == "source"
    assert body["patch"]["changes"]["complaint_category"]["provenance"] == "inferred"
    assert "assistant_message" in body


def test_assistant_message_over_limit_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/assistant/process",
        json={
            "message": "x" * (ASSISTANT_MESSAGE_MAX_LENGTH + 1),
            "fields": empty_fields(),
        },
    )
    assert response.status_code == 422
