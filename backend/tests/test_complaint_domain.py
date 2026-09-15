import pytest
from pydantic import ValidationError

from app.domain.complaint import (
    ComplaintDraft,
    ComplaintFieldKey,
    ComplaintFieldValue,
    ComplaintFields,
    ComplaintPatch,
    ComplaintStatus,
    FieldProvenance,
)


def test_empty_draft_is_pending_triage_with_missing_null_fields() -> None:
    draft = ComplaintDraft()

    assert draft.status == ComplaintStatus.PENDING_TRIAGE
    for field_value in draft.fields.model_dump().values():
        assert field_value["value"] is None
        assert field_value["provenance"] == FieldProvenance.MISSING.value
        assert field_value["confidence"] is None
        assert field_value["evidence"] is None


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_confidence_accepts_unit_interval(confidence: float) -> None:
    field = ComplaintFieldValue(
        value="Amoxicillin Capsules",
        provenance=FieldProvenance.SOURCE,
        confidence=confidence,
        evidence="Amoxicillin Capsules",
    )
    assert field.confidence == confidence


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_rejects_out_of_range(confidence: float) -> None:
    with pytest.raises(ValidationError):
        ComplaintFieldValue(confidence=confidence)


def test_unknown_field_value_properties_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ComplaintFieldValue.model_validate(
            {
                "value": "x",
                "provenance": "user",
                "confidence": None,
                "evidence": None,
                "extra_property": "nope",
            }
        )


def test_complaint_patch_accepts_partial_batch_and_quantity_only() -> None:
    patch = ComplaintPatch.model_validate(
        {
            "changes": {
                "batch_lot_number": {
                    "value": "BMX240602",
                    "provenance": "user",
                    "confidence": None,
                    "evidence": None,
                },
                "affected_quantity": {
                    "value": "48 capsules",
                    "provenance": "user",
                    "confidence": None,
                    "evidence": None,
                },
            }
        }
    )

    assert set(patch.changes.keys()) == {
        ComplaintFieldKey.BATCH_LOT_NUMBER,
        ComplaintFieldKey.AFFECTED_QUANTITY,
    }
    assert patch.changes[ComplaintFieldKey.BATCH_LOT_NUMBER].value == "BMX240602"
    assert patch.changes[ComplaintFieldKey.AFFECTED_QUANTITY].value == "48 capsules"


def test_partial_date_strings_are_preserved_exactly() -> None:
    manufacturing = ComplaintFieldValue(
        value="March 2026",
        provenance=FieldProvenance.SOURCE,
    )
    expiry = ComplaintFieldValue(
        value="February 2028",
        provenance=FieldProvenance.SOURCE,
    )

    assert manufacturing.value == "March 2026"
    assert expiry.value == "February 2028"


def test_complaint_field_key_matches_complaint_fields() -> None:
    enum_keys = {key.value for key in ComplaintFieldKey}
    model_keys = set(ComplaintFields.model_fields.keys())
    assert enum_keys == model_keys
