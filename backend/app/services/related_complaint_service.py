"""Deterministic related-complaint / recurrence scoring against committed history.

This is an explainable decision-support signal. It does not prove that two
records are literal duplicates — a QA reviewer decides the relationship.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Protocol

from app.domain.complaint import (
    ComplaintFields,
    RelatedComplaintMatch,
    RelatedMatchStrength,
    field_value_is_blank,
)
from app.services.related_complaint_config import (
    BATCH_MATCH_WEIGHT,
    CATEGORY_MATCH_WEIGHT,
    CUSTOMER_MATCH_WEIGHT,
    DESCRIPTION_JACCARD_WEIGHT,
    DESCRIPTION_SEQUENCE_WEIGHT,
    DESCRIPTION_SIMILARITY_WEIGHT,
    DESCRIPTION_STOPWORDS,
    MAX_HISTORY_CANDIDATES,
    MAX_RELATED_RESULTS,
    PRODUCT_MATCH_WEIGHT,
    RELATED_COMPLAINT_THRESHOLD,
    STRONG_MATCH_THRESHOLD,
)

logger = logging.getLogger(__name__)

_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class RelatedHistoryRecord:
    """Minimal committed-history projection for scoring (no provenance)."""

    id: uuid.UUID
    complaint_number: str
    product_name: str
    batch_lot_number: str
    customer_name: str
    complaint_category: str
    complaint_description: str
    committed_at: datetime


@dataclass(frozen=True, slots=True)
class RelatedComplaintLookupResult:
    evaluated: bool
    matches: list[RelatedComplaintMatch]


class RelatedComplaintLookup(Protocol):
    def find_related(
        self,
        fields: ComplaintFields,
        *,
        exclude_id: uuid.UUID | None = None,
        limit: int = MAX_RELATED_RESULTS,
    ) -> RelatedComplaintLookupResult: ...


class NoOpRelatedComplaintLookup:
    """Safe default when history lookup is not injected."""

    def find_related(
        self,
        fields: ComplaintFields,
        *,
        exclude_id: uuid.UUID | None = None,
        limit: int = MAX_RELATED_RESULTS,
    ) -> RelatedComplaintLookupResult:
        del fields, exclude_id, limit
        return RelatedComplaintLookupResult(evaluated=False, matches=[])


def normalize_for_comparison(value: str | None) -> str:
    """Comparison-only normalization. Does not mutate stored values."""
    if value is None:
        return ""
    text = value.strip().casefold()
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def normalize_identifier(value: str | None) -> str:
    """Conservative identifier normalization (batch / lot): trim + casefold only."""
    if value is None:
        return ""
    return value.strip().casefold()


def description_tokens(text: str | None) -> set[str]:
    normalized = normalize_for_comparison(text)
    if not normalized:
        return set()
    tokens = {
        token
        for token in normalized.split(" ")
        if token and token not in DESCRIPTION_STOPWORDS
    }
    return tokens


def token_jaccard(left: str | None, right: str | None) -> float:
    a = description_tokens(left)
    b = description_tokens(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def sequence_ratio(left: str | None, right: str | None) -> float:
    a = normalize_for_comparison(left)
    b = normalize_for_comparison(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def description_similarity(left: str | None, right: str | None) -> float:
    """0.6 * token Jaccard + 0.4 * SequenceMatcher ratio."""
    return (
        DESCRIPTION_JACCARD_WEIGHT * token_jaccard(left, right)
        + DESCRIPTION_SEQUENCE_WEIGHT * sequence_ratio(left, right)
    )


def has_sufficient_comparison_data(fields: ComplaintFields) -> bool:
    if field_value_is_blank(fields.product_name.value):
        return False
    return (
        not field_value_is_blank(fields.batch_lot_number.value)
        or not field_value_is_blank(fields.complaint_category.value)
        or not field_value_is_blank(fields.complaint_description.value)
    )


def match_strength_for_score(score: float) -> RelatedMatchStrength:
    if score >= STRONG_MATCH_THRESHOLD:
        return RelatedMatchStrength.STRONG
    return RelatedMatchStrength.MODERATE


def build_match_reasons(
    *,
    product_match: bool,
    batch_match: bool,
    category_match: bool,
    customer_match: bool,
    description_similarity_value: float,
) -> list[str]:
    reasons: list[str] = []
    if product_match:
        reasons.append("Same product")
    if batch_match:
        reasons.append("Same batch / lot")
    if category_match:
        reasons.append("Same complaint category")
    if customer_match:
        reasons.append("Same customer")
    if description_similarity_value >= 0.45:
        reasons.append("Similar complaint description")
    return reasons


def score_candidate(
    draft: ComplaintFields,
    history: RelatedHistoryRecord,
) -> RelatedComplaintMatch | None:
    """Score one historical record. Returns None when gated or below threshold."""
    product_match = normalize_for_comparison(draft.product_name.value) == normalize_for_comparison(
        history.product_name
    )
    batch_match = (
        normalize_identifier(draft.batch_lot_number.value) != ""
        and normalize_identifier(draft.batch_lot_number.value)
        == normalize_identifier(history.batch_lot_number)
    )
    category_match = (
        normalize_for_comparison(draft.complaint_category.value) != ""
        and normalize_for_comparison(draft.complaint_category.value)
        == normalize_for_comparison(history.complaint_category)
    )
    customer_match = (
        normalize_for_comparison(draft.customer_name.value) != ""
        and normalize_for_comparison(draft.customer_name.value)
        == normalize_for_comparison(history.customer_name)
    )
    desc_sim = description_similarity(
        draft.complaint_description.value,
        history.complaint_description,
    )

    # Gating: require at least one structured identity signal.
    if not (product_match or batch_match or category_match):
        return None

    score = (
        (BATCH_MATCH_WEIGHT if batch_match else 0.0)
        + (PRODUCT_MATCH_WEIGHT if product_match else 0.0)
        + (CATEGORY_MATCH_WEIGHT if category_match else 0.0)
        + (DESCRIPTION_SIMILARITY_WEIGHT * desc_sim)
        + (CUSTOMER_MATCH_WEIGHT if customer_match else 0.0)
    )
    score = round(min(1.0, max(0.0, score)), 4)

    if score < RELATED_COMPLAINT_THRESHOLD:
        return None

    reasons = build_match_reasons(
        product_match=product_match,
        batch_match=batch_match,
        category_match=category_match,
        customer_match=customer_match,
        description_similarity_value=desc_sim,
    )
    if not reasons:
        return None

    return RelatedComplaintMatch(
        complaint_id=history.id,
        complaint_number=history.complaint_number,
        score=score,
        match_strength=match_strength_for_score(score),
        reasons=reasons,
        product_name=history.product_name,
        batch_lot_number=history.batch_lot_number,
        customer_name=history.customer_name,
        complaint_category=history.complaint_category,
        complaint_description=history.complaint_description,
        committed_at=history.committed_at,
    )


def rank_related_matches(
    draft: ComplaintFields,
    history_records: list[RelatedHistoryRecord],
    *,
    exclude_id: uuid.UUID | None = None,
    limit: int = MAX_RELATED_RESULTS,
) -> list[RelatedComplaintMatch]:
    matches: list[RelatedComplaintMatch] = []
    for record in history_records:
        if exclude_id is not None and record.id == exclude_id:
            continue
        scored = score_candidate(draft, record)
        if scored is not None:
            matches.append(scored)
    matches.sort(key=lambda item: (-item.score, item.complaint_number))
    return matches[: max(0, limit)]


class RelatedComplaintService:
    """Scores a draft against a bounded set of committed complaints."""

    def __init__(self, history_loader) -> None:
        # history_loader: callable returning list[RelatedHistoryRecord]
        self._history_loader = history_loader

    def find_related(
        self,
        fields: ComplaintFields,
        *,
        exclude_id: uuid.UUID | None = None,
        limit: int = MAX_RELATED_RESULTS,
    ) -> RelatedComplaintLookupResult:
        if not has_sufficient_comparison_data(fields):
            return RelatedComplaintLookupResult(evaluated=False, matches=[])

        history = self._history_loader(limit=MAX_HISTORY_CANDIDATES)
        matches = rank_related_matches(
            fields,
            history,
            exclude_id=exclude_id,
            limit=limit,
        )
        logger.info(
            "related.lookup evaluated=true candidates=%s matches=%s",
            len(history),
            len(matches),
        )
        return RelatedComplaintLookupResult(evaluated=True, matches=matches)
