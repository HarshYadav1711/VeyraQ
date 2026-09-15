"""Pydantic models for Groq structured outputs. Compatible with strict JSON Schema."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.complaint import ComplaintFieldKey

CorrectionFieldName = Literal[
    "complaint_source",
    "customer_name",
    "product_name",
    "product_strength_grade",
    "batch_lot_number",
    "affected_quantity",
    "manufacturing_date",
    "expiry_date",
    "complaint_date",
    "complaint_category",
    "complaint_description",
    "originating_site_block",
    "impacted_non_product_materials",
    "initial_severity",
    "priority",
    "suggested_next_action",
    "initial_risk_assessment",
]

SeverityName = Literal["Critical", "Major", "Minor"]
PriorityName = Literal["High", "Medium", "Low"]
IntentName = Literal["new_complaint", "correction"]


class ExtractedFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | None
    evidence: str | None


class SourceExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_source: ExtractedFact
    customer_name: ExtractedFact
    product_name: ExtractedFact
    product_strength_grade: ExtractedFact
    batch_lot_number: ExtractedFact
    affected_quantity: ExtractedFact
    manufacturing_date: ExtractedFact
    expiry_date: ExtractedFact
    complaint_date: ExtractedFact
    originating_site_block: ExtractedFact
    impacted_non_product_materials: ExtractedFact


class IntentClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: IntentName


class CorrectionChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: CorrectionFieldName
    value: str | None


class CorrectionExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: list[CorrectionChange]


class RiskAssessmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_category: str | None
    initial_severity: SeverityName | None
    priority: PriorityName | None
    suggested_next_action: str | None
    initial_risk_assessment: str | None


def is_canonical_field(name: str) -> bool:
    return name in {key.value for key in ComplaintFieldKey}
