from typing import TypedDict


class ComplaintGraphState(TypedDict):
    user_message: str
    current_fields: dict[str, object]
    intent: str
    blocked: bool
    source_extraction: dict[str, object]
    source_patch: dict[str, object]
    correction_patch: dict[str, object]
    assessment_patch: dict[str, object]
    merged_fields: dict[str, object]
    missing_required_fields: list[str]
    target_status: str
    assistant_message: str
    warnings: list[str]
    should_assess_risk: bool
    assessment_ran: bool
    request_id: str
