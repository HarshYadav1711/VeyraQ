"""On-demand Investigation Assistance (summary + RCA hypotheses + CAPA suggestions).

Derived analysis only — never mutates ComplaintFields, status, severity, or priority.
Uses one structured Groq call via the existing AIService boundary (no extra LangGraph).
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agents.labels import field_label
from app.agents.prompts import (
    INVESTIGATION_ASSISTANCE_SYSTEM_PROMPT,
    wrap_draft_facts,
    wrap_related_history_context,
)
from app.agents.protocol import AIService
from app.agents.schemas import InvestigationAssistanceResult
from app.domain.complaint import (
    ComplaintFieldKey,
    ComplaintFields,
    field_value_is_blank,
)
from app.services.ai_errors import AIStructuredOutputError
from app.services.related_complaint_service import (
    NoOpRelatedComplaintLookup,
    RelatedComplaintLookup,
    RelatedComplaintLookupResult,
)

logger = logging.getLogger(__name__)

MAX_ROOT_CAUSE_HYPOTHESES = 4
MAX_EVIDENCE_NEEDED = 4
MAX_CAPA_SUGGESTIONS = 6

INVESTIGATION_CONTEXT_FIELDS: tuple[ComplaintFieldKey, ...] = (
    ComplaintFieldKey.COMPLAINT_SOURCE,
    ComplaintFieldKey.CUSTOMER_NAME,
    ComplaintFieldKey.PRODUCT_NAME,
    ComplaintFieldKey.PRODUCT_STRENGTH_GRADE,
    ComplaintFieldKey.BATCH_LOT_NUMBER,
    ComplaintFieldKey.AFFECTED_QUANTITY,
    ComplaintFieldKey.MANUFACTURING_DATE,
    ComplaintFieldKey.EXPIRY_DATE,
    ComplaintFieldKey.COMPLAINT_DATE,
    ComplaintFieldKey.COMPLAINT_CATEGORY,
    ComplaintFieldKey.COMPLAINT_DESCRIPTION,
    ComplaintFieldKey.ORIGINATING_SITE_BLOCK,
    ComplaintFieldKey.IMPACTED_NON_PRODUCT_MATERIALS,
    ComplaintFieldKey.INITIAL_SEVERITY,
    ComplaintFieldKey.PRIORITY,
    ComplaintFieldKey.INITIAL_RISK_ASSESSMENT,
)

INSUFFICIENT_CONTEXT_MESSAGE = (
    "Product Name and Complaint Description are required before "
    "investigation assistance can be generated."
)

SAFE_INVESTIGATION_UNAVAILABLE = (
    "Investigation assistance is temporarily unavailable. Your complaint record has not been changed."
)


class InvestigationValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RootCauseHypothesisDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "material",
        "equipment",
        "method",
        "people",
        "measurement",
        "environment",
        "other",
    ]
    hypothesis: str
    rationale: str
    supporting_fields: list[str] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)


class CapaSuggestionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "immediate_correction",
        "corrective_action",
        "preventive_action",
        "effectiveness_check",
    ]
    action: str
    rationale: str


class InvestigationAssistanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_summary: str
    root_cause_hypotheses: list[RootCauseHypothesisDTO] = Field(default_factory=list)
    capa_suggestions: list[CapaSuggestionDTO] = Field(default_factory=list)
    related_history_used: bool = False


def has_investigation_minimum_context(fields: ComplaintFields) -> bool:
    return not field_value_is_blank(fields.product_name.value) and not field_value_is_blank(
        fields.complaint_description.value
    )


def _populated_field_keys(fields: ComplaintFields) -> set[str]:
    keys: set[str] = set()
    for key in ComplaintFieldKey:
        value = getattr(fields, key.value).value
        if not field_value_is_blank(value):
            keys.add(key.value)
    return keys


def _trim_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None


def _trim_list(items: list[str], *, limit: int) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        text = _trim_text(item)
        if text is None:
            continue
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def sanitize_investigation_result(
    raw: InvestigationAssistanceResult,
    fields: ComplaintFields,
) -> InvestigationAssistanceResponse:
    """Semantic validation beyond JSON schema."""
    populated = _populated_field_keys(fields)
    summary = _trim_text(raw.complaint_summary)
    if summary is None:
        raise AIStructuredOutputError("Investigation summary was empty")

    hypotheses: list[RootCauseHypothesisDTO] = []
    for item in raw.root_cause_hypotheses:
        if len(hypotheses) >= MAX_ROOT_CAUSE_HYPOTHESES:
            break
        hypothesis = _trim_text(item.hypothesis)
        rationale = _trim_text(item.rationale)
        if hypothesis is None or rationale is None:
            continue
        supporting: list[str] = []
        for key in item.supporting_fields:
            if key in populated and key not in supporting:
                supporting.append(key)
        if not supporting:
            continue
        evidence = _trim_list(item.evidence_needed, limit=MAX_EVIDENCE_NEEDED)
        hypotheses.append(
            RootCauseHypothesisDTO(
                category=item.category,
                hypothesis=hypothesis,
                rationale=rationale,
                supporting_fields=supporting,
                evidence_needed=evidence,
            )
        )

    capa_items: list[CapaSuggestionDTO] = []
    for item in raw.capa_suggestions:
        if len(capa_items) >= MAX_CAPA_SUGGESTIONS:
            break
        action = _trim_text(item.action)
        rationale = _trim_text(item.rationale)
        if action is None or rationale is None:
            continue
        capa_items.append(
            CapaSuggestionDTO(
                type=item.type,
                action=action,
                rationale=rationale,
            )
        )

    if not hypotheses and not capa_items:
        raise AIStructuredOutputError("Investigation assistance produced no usable analysis")

    return InvestigationAssistanceResponse(
        complaint_summary=summary,
        root_cause_hypotheses=hypotheses,
        capa_suggestions=capa_items,
        related_history_used=False,
    )


def _draft_facts_text(fields: ComplaintFields) -> str:
    lines: list[str] = []
    for key in INVESTIGATION_CONTEXT_FIELDS:
        value = getattr(fields, key.value).value
        if field_value_is_blank(value):
            continue
        lines.append(f"{field_label(key.value)}: {value}")
    return "\n".join(lines) if lines else "(no populated fields)"


def _related_context_text(result: RelatedComplaintLookupResult) -> str | None:
    if not result.evaluated or not result.matches:
        return None
    blocks: list[str] = []
    for match in result.matches[:3]:
        blocks.append(
            "\n".join(
                [
                    f"Complaint number: {match.complaint_number}",
                    f"Product: {match.product_name}",
                    f"Batch: {match.batch_lot_number}",
                    f"Category: {match.complaint_category}",
                    f"Description: {match.complaint_description}",
                ]
            )
        )
    return "\n\n".join(blocks)


class InvestigationService:
    def __init__(
        self,
        ai_service: AIService,
        related_lookup: RelatedComplaintLookup | None = None,
    ) -> None:
        self._ai = ai_service
        self._related = related_lookup or NoOpRelatedComplaintLookup()

    def generate(self, fields: ComplaintFields) -> InvestigationAssistanceResponse:
        if not has_investigation_minimum_context(fields):
            raise InvestigationValidationError(INSUFFICIENT_CONTEXT_MESSAGE)

        related_used = False
        related_text: str | None = None
        try:
            related_result = self._related.find_related(fields)
            related_text = _related_context_text(related_result)
            related_used = related_text is not None
        except Exception:  # noqa: BLE001 — optional context must not fail analysis
            logger.exception("investigation.related_history_failed")

        user_parts = [wrap_draft_facts(_draft_facts_text(fields))]
        if related_text:
            user_parts.append(wrap_related_history_context(related_text))

        raw = self._ai.structured_completion(
            system_prompt=INVESTIGATION_ASSISTANCE_SYSTEM_PROMPT,
            user_prompt="\n\n".join(user_parts),
            response_model=InvestigationAssistanceResult,
            schema_name="investigation_assistance",
        )
        sanitized = sanitize_investigation_result(raw, fields)
        return sanitized.model_copy(update={"related_history_used": related_used})
