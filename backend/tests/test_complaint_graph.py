from app.agents.graph import build_complaint_graph, build_initial_state, result_patch
from app.agents.merge import fields_from_dump
from app.agents.schemas import (
    CorrectionChange,
    CorrectionExtraction,
    IntentClassification,
    RiskAssessmentResult,
)
from app.domain.complaint import (
    ComplaintFieldKey,
    ComplaintFieldValue,
    ComplaintFields,
    FieldProvenance,
)
from tests.fakes.ai_service import FakeAIService, empty_source_extraction, extracted_fact

APOLLO_TEXT = (
    "Apollo Pharmacy reported discolored Amoxicillin Capsules "
    "500 mg from batch AMX240602. Manufactured March 2026 and "
    "expires February 2028."
)

EMAIL_APOLLO_TEXT = (
    "Email from Apollo Pharmacy reported discolored Amoxicillin Capsules "
    "500 mg from batch AMX240602. Manufactured March 2026 and "
    "expires February 2028."
)


def _run(service: FakeAIService, message: str, fields: ComplaintFields | None = None):
    graph = build_complaint_graph(service)
    return graph.invoke(
        build_initial_state(
            user_message=message,
            fields=fields or ComplaintFields(),
            request_id="test-request",
        )
    )


def _field(
    value: str,
    provenance: FieldProvenance = FieldProvenance.SOURCE,
) -> ComplaintFieldValue:
    return ComplaintFieldValue(value=value, provenance=provenance, confidence=None, evidence=None)


def populated_draft() -> ComplaintFields:
    fields = ComplaintFields()
    fields.product_name = _field("Amoxicillin Capsules")
    fields.product_strength_grade = _field("500 mg")
    fields.batch_lot_number = _field("AMX240602")
    fields.affected_quantity = _field("12 capsules")
    fields.customer_name = _field("Apollo Pharmacy")
    fields.complaint_description = _field(APOLLO_TEXT)
    fields.complaint_source = _field("Email")
    fields.complaint_category = ComplaintFieldValue(
        value="Appearance / discoloration",
        provenance=FieldProvenance.INFERRED,
        confidence=None,
        evidence=None,
    )
    fields.initial_risk_assessment = ComplaintFieldValue(
        value="Potential quality defect requiring review.",
        provenance=FieldProvenance.INFERRED,
        confidence=None,
        evidence=None,
    )
    return fields


def grounded_apollo_extraction(*, include_quantity: bool = False, include_source: bool = False):
    overrides = {
        "customer_name": extracted_fact("Apollo Pharmacy", "Apollo Pharmacy"),
        "product_name": extracted_fact("Amoxicillin Capsules", "Amoxicillin Capsules"),
        "product_strength_grade": extracted_fact("500 mg", "500 mg"),
        "batch_lot_number": extracted_fact("AMX240602", "AMX240602"),
        "manufacturing_date": extracted_fact("March 2026", "March 2026"),
        "expiry_date": extracted_fact("February 2028", "February 2028"),
    }
    if include_quantity:
        overrides["affected_quantity"] = extracted_fact("12 capsules", "12 capsules")
    if include_source:
        overrides["complaint_source"] = extracted_fact("Email", "Email")
    return empty_source_extraction(**overrides)


def advisory_risk() -> RiskAssessmentResult:
    return RiskAssessmentResult(
        complaint_category="Appearance / discoloration",
        initial_severity="Major",
        priority="High",
        suggested_next_action="Quarantine remaining pack and open a QA investigation.",
        initial_risk_assessment="Discoloration of a finished capsule lot may indicate a quality defect and should be investigated before further distribution.",
    )


def test_empty_draft_routes_to_new_complaint_without_intent_call() -> None:
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    result = _run(service, APOLLO_TEXT)

    assert result["intent"] == "new_complaint"
    assert "intent_classification" not in service.calls
    assert service.calls[0] == "source_extraction"


def test_grounded_source_value_receives_source_provenance() -> None:
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    result = _run(service, APOLLO_TEXT)
    patch = result_patch(result)

    product = patch.changes[ComplaintFieldKey.PRODUCT_NAME]
    assert product.value == "Amoxicillin Capsules"
    assert product.provenance == FieldProvenance.SOURCE
    assert product.evidence == "Amoxicillin Capsules"


def test_ungrounded_quantity_is_dropped() -> None:
    service = FakeAIService(
        source=grounded_apollo_extraction(include_quantity=True),
        risk=advisory_risk(),
    )
    result = _run(service, APOLLO_TEXT)
    patch = result_patch(result)

    assert ComplaintFieldKey.AFFECTED_QUANTITY not in patch.changes
    assert "ungrounded_evidence:affected_quantity" in result["warnings"]


def test_partial_dates_are_preserved_exactly() -> None:
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    result = _run(service, APOLLO_TEXT)
    patch = result_patch(result)

    assert patch.changes[ComplaintFieldKey.MANUFACTURING_DATE].value == "March 2026"
    assert patch.changes[ComplaintFieldKey.EXPIRY_DATE].value == "February 2028"


def test_complaint_description_preserves_supplied_text() -> None:
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    result = _run(service, APOLLO_TEXT)
    patch = result_patch(result)
    description = patch.changes[ComplaintFieldKey.COMPLAINT_DESCRIPTION]
    assert description.value == APOLLO_TEXT
    assert description.provenance == FieldProvenance.SOURCE


def test_assessment_fields_are_inferred() -> None:
    service = FakeAIService(source=grounded_apollo_extraction(), risk=advisory_risk())
    result = _run(service, APOLLO_TEXT)
    patch = result_patch(result)

    assert patch.changes[ComplaintFieldKey.COMPLAINT_CATEGORY].provenance == FieldProvenance.INFERRED
    assert patch.changes[ComplaintFieldKey.INITIAL_SEVERITY].value == "Major"
    assert patch.changes[ComplaintFieldKey.INITIAL_SEVERITY].provenance == FieldProvenance.INFERRED
    assert patch.changes[ComplaintFieldKey.PRIORITY].provenance == FieldProvenance.INFERRED
    assert patch.changes[ComplaintFieldKey.SUGGESTED_NEXT_ACTION].evidence is None
    assert patch.changes[ComplaintFieldKey.INITIAL_RISK_ASSESSMENT].provenance == FieldProvenance.INFERRED


def test_complete_extracted_complaint_is_ready_to_commit() -> None:
    service = FakeAIService(
        source=grounded_apollo_extraction(include_source=True),
        risk=advisory_risk(),
    )
    result = _run(service, EMAIL_APOLLO_TEXT)
    assert result["target_status"] == "ready_to_commit"
    assert result["missing_required_fields"] == []


def test_missing_batch_is_needs_information() -> None:
    extraction = grounded_apollo_extraction(include_source=True)
    extraction.batch_lot_number = extracted_fact()
    service = FakeAIService(source=extraction, risk=advisory_risk())
    result = _run(service, EMAIL_APOLLO_TEXT)

    assert result["target_status"] == "needs_information"
    assert "batch_lot_number" in result["missing_required_fields"]


def test_correction_updates_only_requested_fields() -> None:
    draft = populated_draft()
    product_before = draft.product_name.model_dump()
    service = FakeAIService(
        intent=IntentClassification(intent="correction"),
        correction=CorrectionExtraction(
            changes=[
                CorrectionChange(field="batch_lot_number", value="BMX240602"),
                CorrectionChange(field="affected_quantity", value="48 capsules"),
            ]
        ),
        risk=advisory_risk(),
    )
    result = _run(
        service,
        "Sorry, batch is BMX240602 and affected quantity is 48 capsules.",
        draft,
    )
    merged = fields_from_dump(result["merged_fields"])
    patch = result_patch(result)

    assert patch.changes[ComplaintFieldKey.BATCH_LOT_NUMBER].value == "BMX240602"
    assert patch.changes[ComplaintFieldKey.AFFECTED_QUANTITY].value == "48 capsules"
    assert ComplaintFieldKey.PRODUCT_NAME not in patch.changes
    assert merged.product_name.model_dump() == product_before
    assert merged.product_name.value == "Amoxicillin Capsules"


def test_correction_fields_have_user_provenance() -> None:
    service = FakeAIService(
        intent=IntentClassification(intent="correction"),
        correction=CorrectionExtraction(
            changes=[
                CorrectionChange(field="batch_lot_number", value="BMX240602"),
                CorrectionChange(field="affected_quantity", value="48 capsules"),
            ]
        ),
        risk=advisory_risk(),
    )
    result = _run(
        service,
        "Sorry, batch is BMX240602 and affected quantity is 48 capsules.",
        populated_draft(),
    )
    patch = result_patch(result)
    assert patch.changes[ComplaintFieldKey.BATCH_LOT_NUMBER].provenance == FieldProvenance.USER
    assert patch.changes[ComplaintFieldKey.AFFECTED_QUANTITY].provenance == FieldProvenance.USER
    assert patch.changes[ComplaintFieldKey.BATCH_LOT_NUMBER].evidence is None


def test_risk_relevant_correction_refreshes_assessment() -> None:
    service = FakeAIService(
        intent=IntentClassification(intent="correction"),
        correction=CorrectionExtraction(
            changes=[CorrectionChange(field="batch_lot_number", value="BMX240602")]
        ),
        risk=RiskAssessmentResult(
            complaint_category="Appearance / discoloration",
            initial_severity="Major",
            priority="High",
            suggested_next_action="Re-evaluate the implicated lot.",
            initial_risk_assessment="Updated lot identity still requires investigation.",
        ),
    )
    result = _run(
        service,
        "Sorry, batch is BMX240602",
        populated_draft(),
    )
    assert "risk_assessment" in service.calls
    patch = result_patch(result)
    assert ComplaintFieldKey.INITIAL_RISK_ASSESSMENT in patch.changes
    assert (
        patch.changes[ComplaintFieldKey.INITIAL_RISK_ASSESSMENT].value
        == "Updated lot identity still requires investigation."
    )


def test_non_risk_relevant_correction_skips_assessment() -> None:
    service = FakeAIService(
        intent=IntentClassification(intent="correction"),
        correction=CorrectionExtraction(
            changes=[CorrectionChange(field="customer_name", value="Northbridge Pharmacy")]
        ),
    )
    result = _run(
        service,
        "The customer name is Northbridge Pharmacy.",
        populated_draft(),
    )
    assert "risk_assessment" not in service.calls
    patch = result_patch(result)
    assert ComplaintFieldKey.CUSTOMER_NAME in patch.changes
    assert ComplaintFieldKey.INITIAL_RISK_ASSESSMENT not in patch.changes


def test_explicit_clear_sets_missing_expiry() -> None:
    draft = populated_draft()
    draft.expiry_date = _field("February 2028")
    service = FakeAIService(
        intent=IntentClassification(intent="correction"),
        correction=CorrectionExtraction(
            changes=[CorrectionChange(field="expiry_date", value=None)]
        ),
    )
    result = _run(service, "Remove the expiry date; we don't have it.", draft)
    patch = result_patch(result)
    expiry = patch.changes[ComplaintFieldKey.EXPIRY_DATE]
    assert expiry.value is None
    assert expiry.provenance == FieldProvenance.MISSING
    merged = fields_from_dump(result["merged_fields"])
    assert merged.product_name.value == "Amoxicillin Capsules"


def test_populated_draft_new_complaint_does_not_overwrite() -> None:
    draft = populated_draft()
    product_before = draft.product_name.model_dump()
    service = FakeAIService(
        intent=IntentClassification(intent="new_complaint"),
        source=grounded_apollo_extraction(),
        risk=advisory_risk(),
    )
    result = _run(
        service,
        "A different pharmacy reported a broken tablet from another product.",
        draft,
    )
    merged = fields_from_dump(result["merged_fields"])
    patch = result_patch(result)

    assert result["blocked"] is True
    assert result["intent"] == "new_complaint"
    assert patch.changes == {}
    assert merged.product_name.model_dump() == product_before
    assert "source_extraction" not in service.calls
    assert "existing" in result["assistant_message"].lower() or "new complaint" in result["assistant_message"].lower()


def test_pharmacy_category_source_accepted_with_customer_name() -> None:
    extraction = grounded_apollo_extraction()
    extraction.complaint_source = extracted_fact("Pharmacy", "Apollo Pharmacy")
    service = FakeAIService(source=extraction, risk=advisory_risk())
    result = _run(service, APOLLO_TEXT)
    patch = result_patch(result)

    assert patch.changes[ComplaintFieldKey.CUSTOMER_NAME].value == "Apollo Pharmacy"
    assert patch.changes[ComplaintFieldKey.CUSTOMER_NAME].provenance == FieldProvenance.SOURCE
    assert patch.changes[ComplaintFieldKey.COMPLAINT_SOURCE].value == "Pharmacy"
    assert patch.changes[ComplaintFieldKey.COMPLAINT_SOURCE].provenance == FieldProvenance.SOURCE
    assert patch.changes[ComplaintFieldKey.COMPLAINT_SOURCE].evidence == "Apollo Pharmacy"


def test_complaint_source_equal_to_customer_name_is_rejected() -> None:
    extraction = grounded_apollo_extraction()
    extraction.complaint_source = extracted_fact("Apollo Pharmacy", "Apollo Pharmacy")
    service = FakeAIService(source=extraction, risk=advisory_risk())
    result = _run(service, APOLLO_TEXT)
    patch = result_patch(result)
    merged = fields_from_dump(result["merged_fields"])

    assert patch.changes[ComplaintFieldKey.CUSTOMER_NAME].value == "Apollo Pharmacy"
    assert ComplaintFieldKey.COMPLAINT_SOURCE not in patch.changes
    assert merged.complaint_source.value is None
    assert merged.complaint_source.provenance == FieldProvenance.MISSING
    assert "semantic_reject:complaint_source_equals_customer_name" in result["warnings"]


def test_email_channel_and_company_name_both_accepted() -> None:
    text = (
        "Complaint received by email from ABC Formulations Ltd. regarding "
        "tablet damage."
    )
    extraction = empty_source_extraction(
        customer_name=extracted_fact("ABC Formulations Ltd.", "ABC Formulations Ltd."),
        complaint_source=extracted_fact("Email", "email"),
        product_name=extracted_fact("tablet", "tablet"),
    )
    service = FakeAIService(source=extraction, risk=advisory_risk())
    result = _run(service, text)
    patch = result_patch(result)

    assert patch.changes[ComplaintFieldKey.CUSTOMER_NAME].value == "ABC Formulations Ltd."
    assert patch.changes[ComplaintFieldKey.COMPLAINT_SOURCE].value == "Email"
    assert patch.changes[ComplaintFieldKey.COMPLAINT_SOURCE].evidence == "email"


def test_null_complaint_source_remains_missing_when_unsupported() -> None:
    text = "ABC Formulations Ltd. reported foreign particulate."
    extraction = empty_source_extraction(
        customer_name=extracted_fact("ABC Formulations Ltd.", "ABC Formulations Ltd."),
    )
    service = FakeAIService(source=extraction, risk=advisory_risk())
    result = _run(service, text)
    patch = result_patch(result)
    merged = fields_from_dump(result["merged_fields"])

    assert patch.changes[ComplaintFieldKey.CUSTOMER_NAME].value == "ABC Formulations Ltd."
    assert ComplaintFieldKey.COMPLAINT_SOURCE not in patch.changes
    assert merged.complaint_source.value is None
    assert merged.complaint_source.provenance == FieldProvenance.MISSING


def test_duplicate_source_customer_rejection_yields_needs_information() -> None:
    extraction = grounded_apollo_extraction()
    extraction.complaint_source = extracted_fact("Apollo Pharmacy", "Apollo Pharmacy")
    service = FakeAIService(source=extraction, risk=advisory_risk())
    result = _run(service, APOLLO_TEXT)

    assert result["target_status"] == "needs_information"
    assert "complaint_source" in result["missing_required_fields"]
    assert ComplaintFieldKey.COMPLAINT_SOURCE not in result_patch(result).changes
