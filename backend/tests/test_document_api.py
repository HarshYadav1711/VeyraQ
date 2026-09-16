"""API and graph tests for document complaint intake."""

from __future__ import annotations

from collections.abc import Iterator

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.agents.graph import build_complaint_graph, build_initial_state, result_patch
from app.api.routes.assistant import get_ai_service, get_related_lookup
from app.domain.complaint import (
    ComplaintFieldKey,
    ComplaintFieldValue,
    ComplaintFields,
    FieldProvenance,
)
from app.main import app
from app.services.document_limits import POPULATED_DRAFT_MESSAGE
from app.services.related_complaint_service import NoOpRelatedComplaintLookup
from tests.fakes.ai_service import FakeAIService, empty_source_extraction, extracted_fact
from tests.test_complaint_graph import advisory_risk

CEFIXIME_DOC_TEXT = (
    "Customer: Northstar Pharma Distribution\n"
    "Product: Cefixime Capsules 200 mg\n"
    "Batch: CFX260481\n"
    "Manufacturing date: March 2026\n"
    "Expiry date: February 2028\n"
    "Complaint: Brown discoloration was observed on multiple capsules "
    "during customer inspection."
)


def _pdf_bytes(text: str) -> bytes:
    document = pymupdf.open()
    try:
        page = document.new_page()
        page.insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_related_lookup] = lambda: NoOpRelatedComplaintLookup()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def empty_fields_json() -> str:
    return ComplaintFields().model_dump_json()


def grounded_cefixime_extraction(*, invent_quantity: bool = False):
    overrides = {
        "customer_name": extracted_fact(
            "Northstar Pharma Distribution",
            "Northstar Pharma Distribution",
        ),
        "product_name": extracted_fact(
            "Cefixime Capsules 200 mg",
            "Cefixime Capsules 200 mg",
        ),
        "batch_lot_number": extracted_fact("CFX260481", "CFX260481"),
        "manufacturing_date": extracted_fact("March 2026", "March 2026"),
        "expiry_date": extracted_fact("February 2028", "February 2028"),
    }
    if invent_quantity:
        overrides["affected_quantity"] = extracted_fact("12 capsules", "12 capsules")
    return empty_source_extraction(**overrides)


def complete_risk():
    risk = advisory_risk()
    return risk


def test_document_text_reaches_existing_ai_workflow(client: TestClient) -> None:
    service = FakeAIService(source=grounded_cefixime_extraction(), risk=complete_risk())
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/process-document",
        files={
            "file": ("complaint.pdf", _pdf_bytes(CEFIXIME_DOC_TEXT), "application/pdf"),
        },
        data={"current_fields": empty_fields_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "new_complaint"
    assert body["document"]["document_type"] == "pdf"
    assert body["document"]["filename"] == "complaint.pdf"
    assert body["patch"]["changes"]["product_name"]["value"] == "Cefixime Capsules 200 mg"
    assert "source_extraction" in service.calls
    assert CEFIXIME_DOC_TEXT.split("\n")[0] in body["patch"]["changes"]["complaint_description"]["value"]


def test_empty_draft_document_skips_intent_classifier() -> None:
    service = FakeAIService(source=grounded_cefixime_extraction(), risk=complete_risk())
    graph = build_complaint_graph(service)
    result = graph.invoke(
        build_initial_state(
            user_message=CEFIXIME_DOC_TEXT,
            fields=ComplaintFields(),
            request_id="doc-test",
            input_kind="document",
        )
    )
    assert result["intent"] == "new_complaint"
    assert "intent_classification" not in service.calls
    assert service.calls[0] == "source_extraction"


def test_document_grounding_rejects_invented_quantity() -> None:
    service = FakeAIService(
        source=grounded_cefixime_extraction(invent_quantity=True),
        risk=complete_risk(),
    )
    result = build_complaint_graph(service).invoke(
        build_initial_state(
            user_message=CEFIXIME_DOC_TEXT,
            fields=ComplaintFields(),
            request_id="doc-ground",
            input_kind="document",
        )
    )
    patch = result_patch(result)
    assert ComplaintFieldKey.AFFECTED_QUANTITY not in patch.changes
    assert "ungrounded_evidence:affected_quantity" in result["warnings"]


def test_document_partial_dates_preserved() -> None:
    service = FakeAIService(source=grounded_cefixime_extraction(), risk=complete_risk())
    result = build_complaint_graph(service).invoke(
        build_initial_state(
            user_message=CEFIXIME_DOC_TEXT,
            fields=ComplaintFields(),
            request_id="doc-dates",
            input_kind="document",
        )
    )
    patch = result_patch(result)
    assert patch.changes[ComplaintFieldKey.MANUFACTURING_DATE].value == "March 2026"
    assert patch.changes[ComplaintFieldKey.EXPIRY_DATE].value == "February 2028"


def test_document_source_and_inferred_provenance() -> None:
    service = FakeAIService(source=grounded_cefixime_extraction(), risk=complete_risk())
    result = build_complaint_graph(service).invoke(
        build_initial_state(
            user_message=CEFIXIME_DOC_TEXT,
            fields=ComplaintFields(),
            request_id="doc-prov",
            input_kind="document",
        )
    )
    patch = result_patch(result)
    assert patch.changes[ComplaintFieldKey.PRODUCT_NAME].provenance == FieldProvenance.SOURCE
    assert (
        patch.changes[ComplaintFieldKey.COMPLAINT_CATEGORY].provenance
        == FieldProvenance.INFERRED
    )


def test_complete_document_can_return_ready_to_commit(client: TestClient) -> None:
    text = "Email complaint\n" + CEFIXIME_DOC_TEXT
    source = empty_source_extraction(
        complaint_source=extracted_fact("Email", "Email"),
        customer_name=extracted_fact(
            "Northstar Pharma Distribution",
            "Northstar Pharma Distribution",
        ),
        product_name=extracted_fact(
            "Cefixime Capsules 200 mg",
            "Cefixime Capsules 200 mg",
        ),
        batch_lot_number=extracted_fact("CFX260481", "CFX260481"),
        manufacturing_date=extracted_fact("March 2026", "March 2026"),
        expiry_date=extracted_fact("February 2028", "February 2028"),
    )
    service = FakeAIService(source=source, risk=complete_risk())
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/process-document",
        files={"file": ("ready.txt", text.encode("utf-8"), "text/plain")},
        data={"current_fields": empty_fields_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_to_commit"
    assert "complaint document" in body["assistant_message"].lower()
    assert body["missing_required_fields"] == []


def test_missing_required_returns_needs_information(client: TestClient) -> None:
    service = FakeAIService(source=grounded_cefixime_extraction(), risk=complete_risk())
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/process-document",
        files={
            "file": ("partial.pdf", _pdf_bytes(CEFIXIME_DOC_TEXT), "application/pdf"),
        },
        data={"current_fields": empty_fields_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_information"
    assert "complaint_source" in body["missing_required_fields"]
    assert "from the document" in body["assistant_message"]


def test_populated_draft_returns_409(client: TestClient) -> None:
    fields = ComplaintFields()
    fields.product_name = ComplaintFieldValue(
        value="Existing Product",
        provenance=FieldProvenance.USER,
    )
    service = FakeAIService(unavailable=True)
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/process-document",
        files={
            "file": ("complaint.pdf", _pdf_bytes(CEFIXIME_DOC_TEXT), "application/pdf"),
        },
        data={"current_fields": fields.model_dump_json()},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == POPULATED_DRAFT_MESSAGE
    assert service.calls == []


def test_invalid_current_fields_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/assistant/process-document",
        files={
            "file": ("complaint.txt", b"hello complaint", "text/plain"),
        },
        data={"current_fields": "{not-json"},
    )
    assert response.status_code == 422


def test_ai_failure_after_parsing_returns_503(client: TestClient) -> None:
    service = FakeAIService(unavailable=True)
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/process-document",
        files={
            "file": ("complaint.pdf", _pdf_bytes(CEFIXIME_DOC_TEXT), "application/pdf"),
        },
        data={"current_fields": empty_fields_json()},
    )
    assert response.status_code == 503
    assert "not been changed" in response.json()["detail"]
    serialized = response.text.lower()
    assert "traceback" not in serialized
    assert "groq" not in serialized
    assert "cefixime" not in serialized


def test_missing_groq_key_health_still_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
