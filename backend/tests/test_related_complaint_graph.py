"""Graph and API tests for related-complaint lookup integration."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.agents.graph import build_complaint_graph, build_initial_state, result_patch
from app.agents.schemas import CorrectionChange, CorrectionExtraction, IntentClassification
from app.api.routes.assistant import get_ai_service, get_related_lookup
from app.domain.complaint import (
    ComplaintFieldKey,
    ComplaintFieldValue,
    ComplaintFields,
    FieldProvenance,
    RelatedComplaintMatch,
    RelatedMatchStrength,
)
from app.main import app
from tests.fakes.ai_service import FakeAIService, empty_source_extraction, extracted_fact
from tests.fakes.related_lookup import FakeRelatedComplaintLookup
from tests.test_complaint_graph import (
    APOLLO_TEXT,
    advisory_risk,
    grounded_apollo_extraction,
    populated_draft,
)


def _related_match(**overrides: object) -> RelatedComplaintMatch:
    payload = {
        "complaint_id": UUID("11111111-1111-4111-8111-111111111101"),
        "complaint_number": "CMP-DEMO-0001",
        "score": 0.91,
        "match_strength": RelatedMatchStrength.STRONG,
        "reasons": [
            "Same product",
            "Same batch / lot",
            "Same complaint category",
            "Similar complaint description",
        ],
        "product_name": "Cefixime Capsules 200 mg",
        "batch_lot_number": "CFX260481",
        "customer_name": "Northbridge Pharmacy",
        "complaint_category": "Product Defect – Discoloration",
        "complaint_description": "Brown discoloration observed on multiple capsules.",
        "committed_at": datetime(2026, 3, 10, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return RelatedComplaintMatch.model_validate(payload)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_new_complaint_invokes_related_lookup() -> None:
    related = FakeRelatedComplaintLookup(matches=[_related_match()])
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    result = build_complaint_graph(service, related).invoke(
        build_initial_state(
            user_message=APOLLO_TEXT,
            fields=ComplaintFields(),
            request_id="related-new",
        )
    )
    assert related.calls == 1
    assert result["related_lookup_evaluated"] is True
    assert len(result["related_complaints"]) == 1
    assert "potentially related" in result["assistant_message"]


def test_correction_to_batch_reruns_related_lookup() -> None:
    related = FakeRelatedComplaintLookup(matches=[_related_match()])
    service = FakeAIService(
        intent=IntentClassification(intent="correction"),
        correction=CorrectionExtraction(
            changes=[CorrectionChange(field="batch_lot_number", value="BMX240602")]
        ),
        risk=advisory_risk(),
    )
    result = build_complaint_graph(service, related).invoke(
        build_initial_state(
            user_message="Sorry, batch is BMX240602",
            fields=populated_draft(),
            request_id="related-batch",
        )
    )
    assert related.calls == 1
    assert result["related_lookup_evaluated"] is True


def test_correction_to_manufacturing_date_skips_related_lookup() -> None:
    related = FakeRelatedComplaintLookup(matches=[_related_match()])
    draft = populated_draft()
    draft.manufacturing_date = ComplaintFieldValue(
        value="March 2026",
        provenance=FieldProvenance.SOURCE,
    )
    service = FakeAIService(
        intent=IntentClassification(intent="correction"),
        correction=CorrectionExtraction(
            changes=[CorrectionChange(field="manufacturing_date", value="April 2026")]
        ),
    )
    result = build_complaint_graph(service, related).invoke(
        build_initial_state(
            user_message="Manufacturing date is April 2026",
            fields=draft,
            request_id="related-mfg",
        )
    )
    assert related.calls == 0
    assert result["related_lookup_evaluated"] is False
    assert result["related_complaints"] == []


def test_related_lookup_does_not_alter_severity() -> None:
    related = FakeRelatedComplaintLookup(matches=[_related_match()])
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    result = build_complaint_graph(service, related).invoke(
        build_initial_state(
            user_message=APOLLO_TEXT,
            fields=ComplaintFields(),
            request_id="related-severity",
        )
    )
    patch = result_patch(result)
    assert patch.changes[ComplaintFieldKey.INITIAL_SEVERITY].value == "Major"


def test_related_lookup_does_not_alter_completeness() -> None:
    related = FakeRelatedComplaintLookup(matches=[_related_match()])
    extraction = grounded_apollo_extraction(include_source=True)
    extraction.batch_lot_number = extracted_fact()
    service = FakeAIService(source=extraction, risk=advisory_risk())
    result = build_complaint_graph(service, related).invoke(
        build_initial_state(
            user_message="Email from Apollo Pharmacy reported discolored Amoxicillin Capsules.",
            fields=ComplaintFields(),
            request_id="related-complete",
        )
    )
    assert result["target_status"] == "needs_information"
    assert "batch_lot_number" in result["missing_required_fields"]


def test_related_lookup_failure_still_returns_extraction() -> None:
    related = FakeRelatedComplaintLookup(fail=True)
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    result = build_complaint_graph(service, related).invoke(
        build_initial_state(
            user_message=APOLLO_TEXT,
            fields=ComplaintFields(),
            request_id="related-fail",
        )
    )
    patch = result_patch(result)
    assert ComplaintFieldKey.PRODUCT_NAME in patch.changes
    assert result["related_complaints"] == []
    assert result["related_lookup_evaluated"] is False
    assert "related_lookup_failed" in result["warnings"]


def test_assistant_process_returns_related_complaints(client: TestClient) -> None:
    related = FakeRelatedComplaintLookup(matches=[_related_match()])
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    app.dependency_overrides[get_ai_service] = lambda: service
    app.dependency_overrides[get_related_lookup] = lambda: related
    response = client.post(
        "/api/v1/assistant/process",
        json={
            "message": APOLLO_TEXT,
            "fields": ComplaintFields().model_dump(mode="json"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["related_complaints"]) == 1
    assert body["related_lookup_evaluated"] is True
    assert body["related_complaints"][0]["complaint_number"] == "CMP-DEMO-0001"
    assert body["related_complaints"][0]["match_strength"] == "strong"
    assert "field_metadata" not in body["related_complaints"][0]


def test_document_process_returns_related_complaints(client: TestClient) -> None:
    related = FakeRelatedComplaintLookup(matches=[_related_match()])
    service = FakeAIService(
        source=empty_source_extraction(
            customer_name=extracted_fact("Northstar", "Northstar"),
            product_name=extracted_fact("Cefixime Capsules 200 mg", "Cefixime Capsules 200 mg"),
            batch_lot_number=extracted_fact("CFX260481", "CFX260481"),
        ),
        risk=advisory_risk(),
    )
    app.dependency_overrides[get_ai_service] = lambda: service
    app.dependency_overrides[get_related_lookup] = lambda: related
    response = client.post(
        "/api/v1/assistant/process-document",
        files={"file": ("note.txt", b"Product: Cefixime Capsules 200 mg Batch: CFX260481", "text/plain")},
        data={"current_fields": ComplaintFields().model_dump_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["related_complaints"][0]["complaint_number"] == "CMP-DEMO-0001"
    assert body["patch"]["changes"]["product_name"]["provenance"] == "source"
