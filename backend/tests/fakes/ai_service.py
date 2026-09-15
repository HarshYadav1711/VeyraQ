from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from app.agents.schemas import (
    CorrectionExtraction,
    ExtractedFact,
    IntentClassification,
    RiskAssessmentResult,
    SourceExtractionResult,
)
from app.services.ai_errors import AIServiceUnavailableError

TModel = TypeVar("TModel", bound=BaseModel)

SOURCE_FIELD_NAMES = (
    "complaint_source",
    "customer_name",
    "product_name",
    "product_strength_grade",
    "batch_lot_number",
    "affected_quantity",
    "manufacturing_date",
    "expiry_date",
    "complaint_date",
    "originating_site_block",
    "impacted_non_product_materials",
)


def extracted_fact(value: str | None = None, evidence: str | None = None) -> ExtractedFact:
    return ExtractedFact(value=value, evidence=evidence)


def empty_source_extraction(**overrides: ExtractedFact) -> SourceExtractionResult:
    payload = {name: extracted_fact() for name in SOURCE_FIELD_NAMES}
    payload.update(overrides)
    return SourceExtractionResult.model_validate(payload)


class FakeAIService:
    model_id = "fake-test-model"

    def __init__(
        self,
        *,
        intent: IntentClassification | None = None,
        source: SourceExtractionResult | None = None,
        correction: CorrectionExtraction | None = None,
        risk: RiskAssessmentResult | None = None,
        unavailable: bool = False,
    ) -> None:
        self.intent = intent or IntentClassification(intent="correction")
        self.source = source or empty_source_extraction()
        self.correction = correction or CorrectionExtraction(changes=[])
        self.risk = risk or RiskAssessmentResult(
            complaint_category=None,
            initial_severity=None,
            priority=None,
            suggested_next_action=None,
            initial_risk_assessment=None,
        )
        self.unavailable = unavailable
        self.calls: list[str] = []
        self.handlers: dict[str, Callable[[], BaseModel]] = {}

    def structured_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[TModel],
        schema_name: str,
    ) -> TModel:
        del system_prompt, user_prompt, response_model
        self.calls.append(schema_name)
        if self.unavailable:
            raise AIServiceUnavailableError("AI processing is unavailable")
        if schema_name in self.handlers:
            return self.handlers[schema_name]()  # type: ignore[return-value]
        mapping: dict[str, Any] = {
            "intent_classification": self.intent,
            "source_extraction": self.source,
            "correction_extraction": self.correction,
            "risk_assessment": self.risk,
        }
        if schema_name not in mapping:
            raise AssertionError(f"unexpected schema {schema_name}")
        return mapping[schema_name]
