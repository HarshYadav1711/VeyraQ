"""LangGraph StateGraph factory for text complaint intake and corrections."""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.grounding import (
    can_ground_extracted_fact,
    is_span_in_text,
    normalize_optional_text,
)
from app.agents.labels import field_label
from app.agents.merge import (
    combine_patches,
    empty_patch,
    fields_from_dump,
    fields_to_dump,
    merge_fields,
    patch_field_keys,
    patch_from_dump,
    patch_to_dump,
)
from app.agents.messages import (
    BLOCKED_NEW_COMPLAINT_MESSAGE,
    correction_message,
    new_complaint_message,
)
from app.agents.prompts import (
    CORRECTION_SYSTEM_PROMPT,
    INTENT_SYSTEM_PROMPT,
    RISK_ASSESSMENT_SYSTEM_PROMPT,
    SOURCE_EXTRACTION_SYSTEM_PROMPT,
    wrap_complaint_text,
    wrap_draft_facts,
    wrap_user_message,
)
from app.agents.protocol import AIService
from app.agents.schemas import (
    CorrectionExtraction,
    IntentClassification,
    RiskAssessmentResult,
    SourceExtractionResult,
)
from app.agents.state import ComplaintGraphState
from app.domain.complaint import (
    RISK_RELEVANT_FIELDS,
    SOURCE_EXTRACTION_FIELDS,
    ComplaintFieldKey,
    ComplaintFieldValue,
    ComplaintFields,
    ComplaintPatch,
    ComplaintStatus,
    FieldProvenance,
    RelatedComplaintMatch,
    field_value_is_blank,
    find_missing_required_fields,
    is_complaint_fields_empty,
)
from app.services.related_complaint_config import RELATED_MATCH_FIELDS
from app.services.related_complaint_service import (
    NoOpRelatedComplaintLookup,
    RelatedComplaintLookup,
)

logger = logging.getLogger(__name__)

RouteAfterIntent = Literal["extract_source_facts", "extract_correction_patch", "check_completeness"]
RouteAfterRiskGate = Literal["assess_risk", "lookup_related_complaints"]


def build_initial_state(
    *,
    user_message: str,
    fields: ComplaintFields,
    request_id: str,
    input_kind: Literal["text", "document"] = "text",
) -> ComplaintGraphState:
    dumped = fields_to_dump(fields)
    return {
        "user_message": user_message,
        "current_fields": dumped,
        "intent": "",
        "blocked": False,
        "input_kind": input_kind,
        "source_extraction": {},
        "source_patch": patch_to_dump(empty_patch()),
        "correction_patch": patch_to_dump(empty_patch()),
        "assessment_patch": patch_to_dump(empty_patch()),
        "merged_fields": dumped,
        "missing_required_fields": [],
        "target_status": ComplaintStatus.PENDING_TRIAGE.value,
        "assistant_message": "",
        "warnings": [],
        "should_assess_risk": False,
        "assessment_ran": False,
        "related_complaints": [],
        "related_lookup_evaluated": False,
        "request_id": request_id,
    }


def _log_node(name: str, request_id: str) -> None:
    logger.info("graph.node name=%s request_id=%s", name, request_id)


def _draft_facts_text(fields: ComplaintFields) -> str:
    lines: list[str] = []
    for key in ComplaintFieldKey:
        value = getattr(fields, key.value).value
        if field_value_is_blank(value):
            continue
        lines.append(f"{field_label(key.value)}: {value}")
    return "\n".join(lines) if lines else "(no populated fields)"


def _source_value(value: str | None, evidence: str | None) -> ComplaintFieldValue:
    return ComplaintFieldValue(
        value=value,
        provenance=FieldProvenance.SOURCE,
        confidence=None,
        evidence=evidence,
    )


def _user_value(value: str) -> ComplaintFieldValue:
    return ComplaintFieldValue(
        value=value,
        provenance=FieldProvenance.USER,
        confidence=None,
        evidence=None,
    )


def _missing_value() -> ComplaintFieldValue:
    return ComplaintFieldValue(
        value=None,
        provenance=FieldProvenance.MISSING,
        confidence=None,
        evidence=None,
    )


def _inferred_value(value: str) -> ComplaintFieldValue:
    return ComplaintFieldValue(
        value=value,
        provenance=FieldProvenance.INFERRED,
        confidence=None,
        evidence=None,
    )


def _has_risk_context(fields: ComplaintFields) -> bool:
    return not field_value_is_blank(fields.product_name.value) and not field_value_is_blank(
        fields.complaint_description.value
    )


def build_complaint_graph(
    ai_service: AIService,
    related_lookup: RelatedComplaintLookup | None = None,
):
    lookup: RelatedComplaintLookup = related_lookup or NoOpRelatedComplaintLookup()
    def determine_intent(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("determine_intent", state["request_id"])
        current = fields_from_dump(state["current_fields"])
        if is_complaint_fields_empty(current):
            return {"intent": "new_complaint", "blocked": False}

        classification = ai_service.structured_completion(
            system_prompt=INTENT_SYSTEM_PROMPT,
            user_prompt=(
                f"{wrap_draft_facts(_draft_facts_text(current))}\n\n"
                f"{wrap_user_message(state['user_message'])}"
            ),
            response_model=IntentClassification,
            schema_name="intent_classification",
        )
        if classification.intent == "new_complaint":
            return {"intent": "new_complaint", "blocked": True}
        return {"intent": "correction", "blocked": False}

    def extract_source_facts(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("extract_source_facts", state["request_id"])
        extraction = ai_service.structured_completion(
            system_prompt=SOURCE_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=wrap_complaint_text(state["user_message"]),
            response_model=SourceExtractionResult,
            schema_name="source_extraction",
        )
        return {"source_extraction": extraction.model_dump(mode="json")}

    def verify_and_build_source_patch(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("verify_and_build_source_patch", state["request_id"])
        extraction = SourceExtractionResult.model_validate(state["source_extraction"])
        source_text = state["user_message"]
        changes: dict[ComplaintFieldKey, ComplaintFieldValue] = {}
        warnings = list(state["warnings"])

        for key in SOURCE_EXTRACTION_FIELDS:
            fact = getattr(extraction, key.value)
            value = normalize_optional_text(fact.value)
            evidence = normalize_optional_text(fact.evidence)
            if value is None:
                continue
            if not can_ground_extracted_fact(value, evidence, source_text):
                warnings.append(f"ungrounded_evidence:{key.value}")
                continue
            changes[key] = _source_value(value, evidence)

        description = normalize_optional_text(source_text)
        if description is not None:
            changes[ComplaintFieldKey.COMPLAINT_DESCRIPTION] = ComplaintFieldValue(
                value=description,
                provenance=FieldProvenance.SOURCE,
                confidence=None,
                evidence=None,
            )

        return {
            "source_patch": patch_to_dump(ComplaintPatch(changes=changes)),
            "warnings": warnings,
        }

    def extract_correction_patch(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("extract_correction_patch", state["request_id"])
        current = fields_from_dump(state["current_fields"])
        extraction = ai_service.structured_completion(
            system_prompt=CORRECTION_SYSTEM_PROMPT,
            user_prompt=(
                f"{wrap_draft_facts(_draft_facts_text(current))}\n\n"
                f"{wrap_user_message(state['user_message'])}"
            ),
            response_model=CorrectionExtraction,
            schema_name="correction_extraction",
        )
        return {"source_extraction": extraction.model_dump(mode="json")}

    def validate_correction(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("validate_correction", state["request_id"])
        extraction = CorrectionExtraction.model_validate(state["source_extraction"])
        changes: dict[ComplaintFieldKey, ComplaintFieldValue] = {}
        warnings = list(state["warnings"])
        message = state["user_message"]

        for item in extraction.changes:
            try:
                field_key = ComplaintFieldKey(item.field)
            except ValueError:
                warnings.append(f"unknown_correction_field:{item.field}")
                continue
            value = normalize_optional_text(item.value)
            if value is None:
                changes[field_key] = _missing_value()
                continue
            if not is_span_in_text(value, message):
                warnings.append(f"ungrounded_correction:{field_key.value}")
                continue
            changes[field_key] = _user_value(value)

        return {"correction_patch": patch_to_dump(ComplaintPatch(changes=changes)), "warnings": warnings}

    def merge_patch(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("merge_patch", state["request_id"])
        current = fields_from_dump(state["current_fields"])
        combined = combine_patches(
            patch_from_dump(state["source_patch"]),
            patch_from_dump(state["correction_patch"]),
        )
        merged = merge_fields(current, combined)
        return {"merged_fields": fields_to_dump(merged)}

    def should_assess_risk(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("should_assess_risk", state["request_id"])
        merged = fields_from_dump(state["merged_fields"])
        if not _has_risk_context(merged):
            return {"should_assess_risk": False}

        if state["intent"] == "new_complaint":
            return {"should_assess_risk": True}

        correction = patch_from_dump(state["correction_patch"])
        if not patch_field_keys(correction) & RISK_RELEVANT_FIELDS:
            return {"should_assess_risk": False}
        return {"should_assess_risk": True}

    def assess_risk(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("assess_risk", state["request_id"])
        merged = fields_from_dump(state["merged_fields"])
        assessment = ai_service.structured_completion(
            system_prompt=RISK_ASSESSMENT_SYSTEM_PROMPT,
            user_prompt=wrap_draft_facts(_draft_facts_text(merged)),
            response_model=RiskAssessmentResult,
            schema_name="risk_assessment",
        )
        return {"source_extraction": assessment.model_dump(mode="json"), "assessment_ran": True}

    def merge_assessment(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("merge_assessment", state["request_id"])
        assessment = RiskAssessmentResult.model_validate(state["source_extraction"])
        protected = patch_field_keys(patch_from_dump(state["correction_patch"]))
        changes: dict[ComplaintFieldKey, ComplaintFieldValue] = {}
        values = {
            ComplaintFieldKey.COMPLAINT_CATEGORY: assessment.complaint_category,
            ComplaintFieldKey.INITIAL_SEVERITY: assessment.initial_severity,
            ComplaintFieldKey.PRIORITY: assessment.priority,
            ComplaintFieldKey.SUGGESTED_NEXT_ACTION: assessment.suggested_next_action,
            ComplaintFieldKey.INITIAL_RISK_ASSESSMENT: assessment.initial_risk_assessment,
        }
        for key, raw in values.items():
            if key in protected:
                continue
            value = normalize_optional_text(raw)
            if value is None:
                continue
            changes[key] = _inferred_value(value)

        assessment_patch = ComplaintPatch(changes=changes)
        merged = merge_fields(fields_from_dump(state["merged_fields"]), assessment_patch)
        return {
            "assessment_patch": patch_to_dump(assessment_patch),
            "merged_fields": fields_to_dump(merged),
        }

    def lookup_related_complaints(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("lookup_related_complaints", state["request_id"])
        if state["blocked"]:
            return {
                "related_complaints": [],
                "related_lookup_evaluated": False,
            }

        if state["intent"] == "correction":
            correction = patch_from_dump(state["correction_patch"])
            if not patch_field_keys(correction) & RELATED_MATCH_FIELDS:
                return {
                    "related_complaints": list(state["related_complaints"]),
                    "related_lookup_evaluated": False,
                }

        merged = fields_from_dump(state["merged_fields"])
        warnings = list(state["warnings"])
        try:
            result = lookup.find_related(merged)
        except Exception:  # noqa: BLE001 — bonus feature must not fail intake
            logger.exception(
                "related.lookup failed request_id=%s",
                state["request_id"],
            )
            warnings.append("related_lookup_failed")
            return {
                "related_complaints": [],
                "related_lookup_evaluated": False,
                "warnings": warnings,
            }

        serialized = [match.model_dump(mode="json") for match in result.matches]
        return {
            "related_complaints": serialized,
            "related_lookup_evaluated": result.evaluated,
            "warnings": warnings,
        }

    def check_completeness(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("check_completeness", state["request_id"])
        merged = fields_from_dump(state["merged_fields"])
        missing = find_missing_required_fields(merged)
        status = (
            ComplaintStatus.READY_TO_COMMIT
            if not missing
            else ComplaintStatus.NEEDS_INFORMATION
        )
        if state["blocked"]:
            current = fields_from_dump(state["current_fields"])
            missing = find_missing_required_fields(current)
            current_status = (
                ComplaintStatus.READY_TO_COMMIT
                if not missing
                else ComplaintStatus.NEEDS_INFORMATION
            )
            # Keep a populated-but-never-evaluated draft in needs_information
            # unless it already satisfies readiness. Do not invent ready_to_commit.
            if is_complaint_fields_empty(current):
                current_status = ComplaintStatus.PENDING_TRIAGE
            return {
                "merged_fields": fields_to_dump(current),
                "missing_required_fields": missing,
                "target_status": current_status.value,
            }
        return {"missing_required_fields": missing, "target_status": status.value}

    def prepare_response(state: ComplaintGraphState) -> dict[str, object]:
        _log_node("prepare_response", state["request_id"])
        status = ComplaintStatus(state["target_status"])
        related_count = (
            len(state["related_complaints"]) if state["related_lookup_evaluated"] else 0
        )
        if state["blocked"]:
            return {"assistant_message": BLOCKED_NEW_COMPLAINT_MESSAGE}

        if state["intent"] == "correction":
            message = correction_message(
                correction_patch=patch_from_dump(state["correction_patch"]),
                assessment_ran=state["assessment_ran"],
                status=status,
                missing_required_fields=state["missing_required_fields"],
                related_count=related_count,
            )
            return {"assistant_message": message}

        message = new_complaint_message(
            source_patch=patch_from_dump(state["source_patch"]),
            assessment_ran=state["assessment_ran"],
            status=status,
            missing_required_fields=state["missing_required_fields"],
            input_kind=state["input_kind"],
            related_count=related_count,
        )
        return {"assistant_message": message}

    def route_intent(state: ComplaintGraphState) -> RouteAfterIntent:
        if state["blocked"]:
            return "check_completeness"
        if state["intent"] == "correction":
            return "extract_correction_patch"
        return "extract_source_facts"

    def route_risk(state: ComplaintGraphState) -> RouteAfterRiskGate:
        if state["should_assess_risk"]:
            return "assess_risk"
        return "lookup_related_complaints"

    builder = StateGraph(ComplaintGraphState)
    builder.add_node("determine_intent", determine_intent)
    builder.add_node("extract_source_facts", extract_source_facts)
    builder.add_node("verify_and_build_source_patch", verify_and_build_source_patch)
    builder.add_node("extract_correction_patch", extract_correction_patch)
    builder.add_node("validate_correction", validate_correction)
    builder.add_node("merge_patch", merge_patch)
    builder.add_node("should_assess_risk", should_assess_risk)
    builder.add_node("assess_risk", assess_risk)
    builder.add_node("merge_assessment", merge_assessment)
    builder.add_node("lookup_related_complaints", lookup_related_complaints)
    builder.add_node("check_completeness", check_completeness)
    builder.add_node("prepare_response", prepare_response)

    builder.add_edge(START, "determine_intent")
    builder.add_conditional_edges(
        "determine_intent",
        route_intent,
        {
            "extract_source_facts": "extract_source_facts",
            "extract_correction_patch": "extract_correction_patch",
            "check_completeness": "check_completeness",
        },
    )
    builder.add_edge("extract_source_facts", "verify_and_build_source_patch")
    builder.add_edge("verify_and_build_source_patch", "merge_patch")
    builder.add_edge("extract_correction_patch", "validate_correction")
    builder.add_edge("validate_correction", "merge_patch")
    builder.add_edge("merge_patch", "should_assess_risk")
    builder.add_conditional_edges(
        "should_assess_risk",
        route_risk,
        {
            "assess_risk": "assess_risk",
            "lookup_related_complaints": "lookup_related_complaints",
        },
    )
    builder.add_edge("assess_risk", "merge_assessment")
    builder.add_edge("merge_assessment", "lookup_related_complaints")
    builder.add_edge("lookup_related_complaints", "check_completeness")
    builder.add_edge("check_completeness", "prepare_response")
    builder.add_edge("prepare_response", END)
    return builder.compile()


def result_patch(state: ComplaintGraphState) -> ComplaintPatch:
    return combine_patches(
        patch_from_dump(state["source_patch"]),
        patch_from_dump(state["correction_patch"]),
        patch_from_dump(state["assessment_patch"]),
    )


def result_related_complaints(state: ComplaintGraphState) -> list[RelatedComplaintMatch]:
    matches: list[RelatedComplaintMatch] = []
    for item in state["related_complaints"]:
        matches.append(RelatedComplaintMatch.model_validate(item))
    return matches
