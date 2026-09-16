"""Investigation Assistance service and API tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agents.schemas import (
    CapaSuggestionModel,
    InvestigationAssistanceResult,
    RootCauseHypothesisModel,
)
from app.api.routes.assistant import get_ai_service, get_related_lookup
from app.domain.complaint import (
    ComplaintFieldValue,
    ComplaintFields,
    FieldProvenance,
)
from app.main import app
from app.services.ai_errors import AIStructuredOutputError
from app.services.investigation_service import (
    InvestigationService,
    InvestigationValidationError,
    sanitize_investigation_result,
)
from app.services.related_complaint_service import NoOpRelatedComplaintLookup
from tests.fakes.ai_service import FakeAIService
from tests.fakes.related_lookup import FakeRelatedComplaintLookup
from app.domain.complaint import RelatedComplaintMatch, RelatedMatchStrength


def _field(value: str | None) -> ComplaintFieldValue:
    if value is None:
        return ComplaintFieldValue()
    return ComplaintFieldValue(value=value, provenance=FieldProvenance.SOURCE)


def minimal_fields(
    *,
    product_name: str | None = "Cefixime Capsules 200 mg",
    complaint_description: str | None = (
        "Brown discoloration was observed on several capsules."
    ),
    complaint_category: str | None = "Product Defect – Discoloration",
    expiry_date: str | None = None,
    batch_lot_number: str | None = None,
) -> ComplaintFields:
    fields = ComplaintFields()
    fields.product_name = _field(product_name)
    fields.complaint_description = _field(complaint_description)
    fields.complaint_category = _field(complaint_category)
    fields.expiry_date = _field(expiry_date)
    fields.batch_lot_number = _field(batch_lot_number)
    return fields


def sample_raw_result(**overrides: object) -> InvestigationAssistanceResult:
    payload = {
        "complaint_summary": (
            "A customer reported brown discoloration on Cefixime Capsules 200 mg. "
            "QA should review the complaint details and related batch history."
        ),
        "root_cause_hypotheses": [
            {
                "category": "material",
                "hypothesis": (
                    "Packaging material may have contributed to moisture exposure."
                ),
                "rationale": (
                    "The complaint concerns capsule discoloration and packaging "
                    "should be investigated."
                ),
                "supporting_fields": ["complaint_category", "complaint_description"],
                "evidence_needed": [
                    "Packaging material records",
                    "Container-closure inspection",
                    "Retain sample review",
                ],
            }
        ],
        "capa_suggestions": [
            {
                "type": "immediate_correction",
                "action": "Quarantine remaining implicated stock pending QA review.",
                "rationale": "Containment while the discoloration complaint is investigated.",
            },
            {
                "type": "corrective_action",
                "action": (
                    "If investigation confirms a packaging contribution, review packaging "
                    "controls for the implicated lot."
                ),
                "rationale": "Addresses a potential packaging-related cause if supported.",
            },
        ],
    }
    payload.update(overrides)
    return InvestigationAssistanceResult.model_validate(payload)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_related_lookup] = lambda: NoOpRelatedComplaintLookup()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_investigation_schema_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        InvestigationAssistanceResult.model_validate(
            {
                **sample_raw_result().model_dump(),
                "secret_chain_of_thought": "hidden",
            }
        )


def test_investigation_schema_constrains_category_and_capa_type() -> None:
    with pytest.raises(ValidationError):
        RootCauseHypothesisModel.model_validate(
            {
                "category": "not_a_real_category",
                "hypothesis": "x",
                "rationale": "y",
                "supporting_fields": ["product_name"],
                "evidence_needed": [],
            }
        )
    with pytest.raises(ValidationError):
        CapaSuggestionModel.model_validate(
            {
                "type": "approved_capa",
                "action": "Do something",
                "rationale": "Because",
            }
        )


def test_semantic_validation_trims_list_limits() -> None:
    raw = sample_raw_result(
        root_cause_hypotheses=[
            {
                "category": "material",
                "hypothesis": f"Hypothesis {index}",
                "rationale": f"Rationale {index}",
                "supporting_fields": ["complaint_description"],
                "evidence_needed": [f"Evidence {n}" for n in range(8)],
            }
            for index in range(6)
        ],
        capa_suggestions=[
            {
                "type": "preventive_action",
                "action": f"Action {index}",
                "rationale": f"Why {index}",
            }
            for index in range(8)
        ],
    )
    fields = minimal_fields()
    result = sanitize_investigation_result(raw, fields)
    assert len(result.root_cause_hypotheses) == 4
    assert len(result.root_cause_hypotheses[0].evidence_needed) == 4
    assert len(result.capa_suggestions) == 6


def test_supporting_fields_filter_blank_and_drop_unsupported_hypothesis() -> None:
    fields = minimal_fields(expiry_date=None)
    raw = sample_raw_result(
        root_cause_hypotheses=[
            {
                "category": "material",
                "hypothesis": "Packaging may be involved.",
                "rationale": "Category and description support review.",
                "supporting_fields": ["complaint_category", "expiry_date"],
                "evidence_needed": ["Packaging records"],
            },
            {
                "category": "equipment",
                "hypothesis": "Equipment may be involved.",
                "rationale": "Only empty fields cited.",
                "supporting_fields": ["expiry_date", "manufacturing_date"],
                "evidence_needed": ["Equipment log"],
            },
        ]
    )
    result = sanitize_investigation_result(raw, fields)
    assert len(result.root_cause_hypotheses) == 1
    assert result.root_cause_hypotheses[0].supporting_fields == ["complaint_category"]


def test_unusable_result_raises() -> None:
    fields = minimal_fields()
    raw = sample_raw_result(
        complaint_summary="   ",
        root_cause_hypotheses=[],
        capa_suggestions=[],
    )
    with pytest.raises(AIStructuredOutputError):
        sanitize_investigation_result(raw, fields)


def test_missing_product_returns_422(client: TestClient) -> None:
    service = FakeAIService()
    app.dependency_overrides[get_ai_service] = lambda: service
    fields = minimal_fields(product_name=None)
    response = client.post(
        "/api/v1/assistant/investigation",
        json={"fields": fields.model_dump(mode="json")},
    )
    assert response.status_code == 422
    assert "Product Name" in response.json()["detail"]
    assert service.calls == []


def test_missing_description_returns_422(client: TestClient) -> None:
    service = FakeAIService()
    app.dependency_overrides[get_ai_service] = lambda: service
    fields = minimal_fields(complaint_description=None)
    response = client.post(
        "/api/v1/assistant/investigation",
        json={"fields": fields.model_dump(mode="json")},
    )
    assert response.status_code == 422
    assert service.calls == []


def test_valid_minimum_calls_ai_service(client: TestClient) -> None:
    service = FakeAIService()
    service.handlers["investigation_assistance"] = sample_raw_result
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/investigation",
        json={"fields": minimal_fields().model_dump(mode="json")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "complaint_summary" in body
    assert body["root_cause_hypotheses"]
    assert body["capa_suggestions"]
    assert "investigation_assistance" in service.calls
    assert "patch" not in body
    assert "status" not in body


def test_provider_unavailable_returns_safe_503(client: TestClient) -> None:
    service = FakeAIService(unavailable=True)
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/investigation",
        json={"fields": minimal_fields().model_dump(mode="json")},
    )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "not been changed" in detail
    assert "traceback" not in response.text.lower()
    assert "groq" not in response.text.lower()


def test_related_history_failure_still_succeeds() -> None:
    service = FakeAIService()
    service.handlers["investigation_assistance"] = sample_raw_result
    related = FakeRelatedComplaintLookup(fail=True)
    result = InvestigationService(service, related).generate(minimal_fields())
    assert result.complaint_summary
    assert result.related_history_used is False


def test_related_history_used_when_available() -> None:
    service = FakeAIService()
    service.handlers["investigation_assistance"] = sample_raw_result
    related = FakeRelatedComplaintLookup(
        matches=[
            RelatedComplaintMatch(
                complaint_id=UUID("11111111-1111-4111-8111-111111111101"),
                complaint_number="CMP-DEMO-0001",
                score=0.91,
                match_strength=RelatedMatchStrength.STRONG,
                reasons=["Same product", "Same batch / lot"],
                product_name="Cefixime Capsules 200 mg",
                batch_lot_number="CFX260481",
                customer_name="Northbridge Pharmacy",
                complaint_category="Product Defect – Discoloration",
                complaint_description="Brown discoloration observed.",
                committed_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
            )
        ]
    )
    result = InvestigationService(service, related).generate(
        minimal_fields(batch_lot_number="CFX260481")
    )
    assert result.related_history_used is True
    assert related.calls == 1


def test_endpoint_does_not_return_complaint_patch(client: TestClient) -> None:
    service = FakeAIService()
    service.handlers["investigation_assistance"] = sample_raw_result
    app.dependency_overrides[get_ai_service] = lambda: service
    before = minimal_fields().model_dump(mode="json")
    response = client.post(
        "/api/v1/assistant/investigation",
        json={"fields": before},
    )
    assert response.status_code == 200
    assert response.json().get("patch") is None


def test_process_endpoints_do_not_call_investigation(client: TestClient) -> None:
    from tests.fakes.ai_service import empty_source_extraction, extracted_fact
    from tests.test_complaint_graph import advisory_risk

    service = FakeAIService(
        source=empty_source_extraction(
            product_name=extracted_fact("Amoxicillin Capsules", "Amoxicillin Capsules")
        ),
        risk=advisory_risk(),
    )
    app.dependency_overrides[get_ai_service] = lambda: service
    response = client.post(
        "/api/v1/assistant/process",
        json={
            "message": "Apollo Pharmacy reported Amoxicillin Capsules discoloration.",
            "fields": ComplaintFields().model_dump(mode="json"),
        },
    )
    assert response.status_code == 200
    assert "investigation_assistance" not in service.calls
