"""Canonical pharmaceutical complaint intake domain contracts."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FieldProvenance(str, Enum):
    SOURCE = "source"
    USER = "user"
    INFERRED = "inferred"
    MISSING = "missing"


class ComplaintStatus(str, Enum):
    PENDING_TRIAGE = "pending_triage"
    PROCESSING = "processing"
    NEEDS_INFORMATION = "needs_information"
    READY_TO_COMMIT = "ready_to_commit"
    COMMITTED = "committed"


class ComplaintFieldKey(str, Enum):
    COMPLAINT_SOURCE = "complaint_source"
    CUSTOMER_NAME = "customer_name"
    PRODUCT_NAME = "product_name"
    PRODUCT_STRENGTH_GRADE = "product_strength_grade"
    BATCH_LOT_NUMBER = "batch_lot_number"
    AFFECTED_QUANTITY = "affected_quantity"
    MANUFACTURING_DATE = "manufacturing_date"
    EXPIRY_DATE = "expiry_date"
    COMPLAINT_DATE = "complaint_date"
    COMPLAINT_CATEGORY = "complaint_category"
    COMPLAINT_DESCRIPTION = "complaint_description"
    ORIGINATING_SITE_BLOCK = "originating_site_block"
    IMPACTED_NON_PRODUCT_MATERIALS = "impacted_non_product_materials"
    INITIAL_SEVERITY = "initial_severity"
    PRIORITY = "priority"
    SUGGESTED_NEXT_ACTION = "suggested_next_action"
    INITIAL_RISK_ASSESSMENT = "initial_risk_assessment"


REQUIRED_COMMIT_FIELDS: tuple[ComplaintFieldKey, ...] = (
    ComplaintFieldKey.COMPLAINT_SOURCE,
    ComplaintFieldKey.CUSTOMER_NAME,
    ComplaintFieldKey.PRODUCT_NAME,
    ComplaintFieldKey.BATCH_LOT_NUMBER,
    ComplaintFieldKey.COMPLAINT_CATEGORY,
    ComplaintFieldKey.COMPLAINT_DESCRIPTION,
    ComplaintFieldKey.INITIAL_RISK_ASSESSMENT,
)

ASSISTANT_MESSAGE_MAX_LENGTH = 12000

SOURCE_EXTRACTION_FIELDS: tuple[ComplaintFieldKey, ...] = (
    ComplaintFieldKey.COMPLAINT_SOURCE,
    ComplaintFieldKey.CUSTOMER_NAME,
    ComplaintFieldKey.PRODUCT_NAME,
    ComplaintFieldKey.PRODUCT_STRENGTH_GRADE,
    ComplaintFieldKey.BATCH_LOT_NUMBER,
    ComplaintFieldKey.AFFECTED_QUANTITY,
    ComplaintFieldKey.MANUFACTURING_DATE,
    ComplaintFieldKey.EXPIRY_DATE,
    ComplaintFieldKey.COMPLAINT_DATE,
    ComplaintFieldKey.ORIGINATING_SITE_BLOCK,
    ComplaintFieldKey.IMPACTED_NON_PRODUCT_MATERIALS,
)

ASSESSMENT_FIELDS: tuple[ComplaintFieldKey, ...] = (
    ComplaintFieldKey.COMPLAINT_CATEGORY,
    ComplaintFieldKey.INITIAL_SEVERITY,
    ComplaintFieldKey.PRIORITY,
    ComplaintFieldKey.SUGGESTED_NEXT_ACTION,
    ComplaintFieldKey.INITIAL_RISK_ASSESSMENT,
)

RISK_RELEVANT_FIELDS: frozenset[ComplaintFieldKey] = frozenset(
    {
        ComplaintFieldKey.PRODUCT_NAME,
        ComplaintFieldKey.PRODUCT_STRENGTH_GRADE,
        ComplaintFieldKey.BATCH_LOT_NUMBER,
        ComplaintFieldKey.AFFECTED_QUANTITY,
        ComplaintFieldKey.COMPLAINT_CATEGORY,
        ComplaintFieldKey.COMPLAINT_DESCRIPTION,
        ComplaintFieldKey.ORIGINATING_SITE_BLOCK,
        ComplaintFieldKey.IMPACTED_NON_PRODUCT_MATERIALS,
    }
)


class FieldMetadataEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provenance: FieldProvenance
    confidence: float | None = None
    evidence: str | None = None

    @field_validator("confidence")
    @classmethod
    def confidence_in_unit_interval(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0.0 or value > 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive")
        return value


class ComplaintFieldValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | None = None
    provenance: FieldProvenance = FieldProvenance.MISSING
    confidence: float | None = None
    evidence: str | None = None

    @field_validator("confidence")
    @classmethod
    def confidence_in_unit_interval(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0.0 or value > 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive")
        return value

    @model_validator(mode="after")
    def provenance_matches_value(self) -> "ComplaintFieldValue":
        if self.value is None and self.provenance != FieldProvenance.MISSING:
            raise ValueError("null values must use missing provenance")
        if self.value is not None and self.provenance == FieldProvenance.MISSING:
            raise ValueError("non-null values cannot use missing provenance")
        return self


class ComplaintFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_source: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    customer_name: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    product_name: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    product_strength_grade: ComplaintFieldValue = Field(
        default_factory=ComplaintFieldValue
    )
    batch_lot_number: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    affected_quantity: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    manufacturing_date: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    expiry_date: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    complaint_date: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    complaint_category: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    complaint_description: ComplaintFieldValue = Field(
        default_factory=ComplaintFieldValue
    )
    originating_site_block: ComplaintFieldValue = Field(
        default_factory=ComplaintFieldValue
    )
    impacted_non_product_materials: ComplaintFieldValue = Field(
        default_factory=ComplaintFieldValue
    )
    initial_severity: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    priority: ComplaintFieldValue = Field(default_factory=ComplaintFieldValue)
    suggested_next_action: ComplaintFieldValue = Field(
        default_factory=ComplaintFieldValue
    )
    initial_risk_assessment: ComplaintFieldValue = Field(
        default_factory=ComplaintFieldValue
    )


def field_value_is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


def find_missing_required_fields(fields: ComplaintFields) -> list[str]:
    missing: list[str] = []
    for key in REQUIRED_COMMIT_FIELDS:
        value = getattr(fields, key.value).value
        if field_value_is_blank(value):
            missing.append(key.value)
    return missing


def is_complaint_fields_empty(fields: ComplaintFields) -> bool:
    for key in ComplaintFieldKey:
        value = getattr(fields, key.value).value
        if not field_value_is_blank(value):
            return False
    return True


class ComplaintPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: dict[ComplaintFieldKey, ComplaintFieldValue] = Field(default_factory=dict)


class ComplaintDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: ComplaintFields = Field(default_factory=ComplaintFields)
    status: ComplaintStatus = ComplaintStatus.PENDING_TRIAGE


class ComplaintCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: ComplaintFields


class CommittedComplaintResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    complaint_number: str
    status: ComplaintStatus = ComplaintStatus.COMMITTED
    fields: ComplaintFields
    created_at: datetime
    committed_at: datetime


class ComplaintListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    complaint_number: str
    status: ComplaintStatus = ComplaintStatus.COMMITTED
    customer_name: str
    product_name: str
    batch_lot_number: str
    complaint_category: str
    committed_at: datetime


class RelatedMatchStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"


class RelatedComplaintMatch(BaseModel):
    """Decision-support signal — not a proven duplicate determination."""

    model_config = ConfigDict(extra="forbid")

    complaint_id: UUID
    complaint_number: str
    score: float
    match_strength: RelatedMatchStrength
    reasons: list[str]
    product_name: str
    batch_lot_number: str
    customer_name: str
    complaint_category: str
    complaint_description: str
    committed_at: datetime

    @field_validator("score")
    @classmethod
    def score_in_unit_interval(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("score must be between 0.0 and 1.0 inclusive")
        return value


class CommitValidationError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
    missing_fields: list[str]
