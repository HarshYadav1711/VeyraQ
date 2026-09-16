"""Pure unit tests for deterministic related-complaint scoring."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.domain.complaint import (
    ComplaintFieldValue,
    ComplaintFields,
    FieldProvenance,
)
from app.services.related_complaint_config import RELATED_COMPLAINT_THRESHOLD
from app.services.related_complaint_service import (
    RelatedComplaintService,
    RelatedHistoryRecord,
    description_similarity,
    has_sufficient_comparison_data,
    normalize_for_comparison,
    normalize_identifier,
    rank_related_matches,
    score_candidate,
)


def _field(value: str | None) -> ComplaintFieldValue:
    if value is None:
        return ComplaintFieldValue()
    return ComplaintFieldValue(value=value, provenance=FieldProvenance.SOURCE)


def _draft(**overrides: str | None) -> ComplaintFields:
    fields = ComplaintFields()
    defaults = {
        "product_name": "Cefixime Capsules 200 mg",
        "batch_lot_number": "CFX260481",
        "complaint_category": "Product Defect – Discoloration",
        "complaint_description": "Brown discoloration observed on several capsules.",
        "customer_name": "Northstar Pharma Distribution",
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        setattr(fields, key, _field(value))
    return fields


def _history(**overrides: object) -> RelatedHistoryRecord:
    payload = {
        "id": uuid.uuid4(),
        "complaint_number": "CMP-DEMO-0001",
        "product_name": "Cefixime Capsules 200 mg",
        "batch_lot_number": "CFX260481",
        "customer_name": "Northbridge Pharmacy",
        "complaint_category": "Product Defect – Discoloration",
        "complaint_description": (
            "Customer observed brown discoloration on multiple capsules."
        ),
        "committed_at": datetime(2026, 3, 10, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return RelatedHistoryRecord(**payload)  # type: ignore[arg-type]


def test_identical_normalized_product_matches() -> None:
    assert normalize_for_comparison("Cefixime Capsules 200 mg") == normalize_for_comparison(
        "cefixime capsules 200 mg"
    )


def test_different_products_do_not_match() -> None:
    assert normalize_for_comparison("Cefixime Capsules 200 mg") != normalize_for_comparison(
        "Metformin Hydrochloride Tablets"
    )


def test_exact_batch_match_succeeds() -> None:
    assert normalize_identifier("CFX260481") == normalize_identifier("cfx260481")
    match = score_candidate(_draft(), _history())
    assert match is not None
    assert "Same batch / lot" in match.reasons


def test_similar_looking_batches_are_not_fuzzy_matched() -> None:
    assert normalize_identifier("CFX260481") != normalize_identifier("CFX260418")
    match = score_candidate(
        _draft(
            batch_lot_number="CFX260481",
            complaint_description="Brown discoloration observed on several capsules.",
        ),
        _history(
            batch_lot_number="CFX260418",
            complaint_description="Brown discoloration observed on several capsules.",
        ),
    )
    assert match is not None
    assert "Same batch / lot" not in match.reasons


def test_identical_categories_match() -> None:
    match = score_candidate(_draft(), _history())
    assert match is not None
    assert "Same complaint category" in match.reasons


def test_description_similarity_high_for_related_narratives() -> None:
    score = description_similarity(
        "Brown discoloration observed on several capsules.",
        "Customer observed brown discoloration on multiple capsules.",
    )
    assert score >= 0.45


def test_generic_unrelated_descriptions_remain_low() -> None:
    score = description_similarity(
        "Bottle seal incomplete on receipt.",
        "API assay result outside specification.",
    )
    assert score < 0.35


def test_same_customer_alone_does_not_cross_threshold() -> None:
    draft = _draft(
        product_name="Unique Product Alpha",
        batch_lot_number="AAA111",
        complaint_category="Labeling Issue",
        complaint_description="Label smear on outer carton.",
        customer_name="Shared Customer Inc",
    )
    history = _history(
        product_name="Totally Different Product",
        batch_lot_number="ZZZ999",
        complaint_category="Foreign Particulate",
        complaint_description="Metal particle found in drum.",
        customer_name="Shared Customer Inc",
    )
    assert score_candidate(draft, history) is None


def test_high_text_similarity_blocked_without_structured_signal() -> None:
    draft = _draft(
        product_name="Product A",
        batch_lot_number="BATCH-A",
        complaint_category="Category A",
        complaint_description="The product was damaged during shipment handling.",
    )
    history = _history(
        product_name="Product B",
        batch_lot_number="BATCH-B",
        complaint_category="Category B",
        complaint_description="The product was damaged during shipment handling.",
    )
    assert score_candidate(draft, history) is None


def test_cefixime_related_pair_is_strong() -> None:
    draft = _draft(
        complaint_description="Brown discoloration observed on several capsules.",
    )
    history = _history(
        complaint_description=(
            "Customer observed brown discoloration on multiple capsules."
        ),
    )
    match = score_candidate(draft, history)
    assert match is not None
    assert match.score >= 0.80
    assert match.match_strength.value == "strong"
    assert match.score >= RELATED_COMPLAINT_THRESHOLD


def test_unrelated_metformin_does_not_rank() -> None:
    draft = _draft()
    history = _history(
        product_name="Metformin Hydrochloride API",
        batch_lot_number="MTH250912",
        complaint_category="Foreign Particulate",
        complaint_description="Dark speck observed in bulk powder sample.",
        customer_name="Summit API Trading",
    )
    assert score_candidate(draft, history) is None


def test_results_sorted_and_limited_and_exclude_id() -> None:
    draft = _draft()
    keep_id = uuid.UUID("11111111-1111-4111-8111-111111111101")
    exclude_id = uuid.UUID("11111111-1111-4111-8111-111111111102")
    history = [
        _history(id=keep_id, complaint_number="CMP-DEMO-0001"),
        _history(
            id=exclude_id,
            complaint_number="CMP-DEMO-0002",
            complaint_description=(
                "Brown discoloration observed on several capsules from the same batch."
            ),
        ),
        _history(
            id=uuid.uuid4(),
            complaint_number="CMP-DEMO-0099",
            batch_lot_number="OTHER",
            complaint_description="Brown discoloration on capsules noted by QA.",
        ),
        _history(
            id=uuid.uuid4(),
            complaint_number="CMP-OTHER",
            product_name="Ibuprofen API",
            batch_lot_number="IBU-1",
            complaint_category="Assay Failure",
            complaint_description="Assay below limit.",
        ),
    ]
    matches = rank_related_matches(draft, history, exclude_id=exclude_id, limit=3)
    assert all(item.complaint_id != exclude_id for item in matches)
    assert len(matches) <= 3
    scores = [item.score for item in matches]
    assert scores == sorted(scores, reverse=True)


def test_empty_history_and_insufficient_data() -> None:
    assert has_sufficient_comparison_data(_draft(product_name=None)) is False
    service = RelatedComplaintService(lambda limit: [])
    result = service.find_related(_draft())
    assert result.evaluated is True
    assert result.matches == []

    skipped = RelatedComplaintService(lambda limit: [_history()]).find_related(
        _draft(product_name=None, batch_lot_number=None, complaint_category=None, complaint_description=None)
    )
    assert skipped.evaluated is False
