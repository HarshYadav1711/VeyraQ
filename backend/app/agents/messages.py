"""Deterministic Assistant messages. No extra LLM phrasing call."""

from app.agents.labels import join_field_labels
from app.domain.complaint import ComplaintFieldKey, ComplaintPatch, ComplaintStatus

BLOCKED_NEW_COMPLAINT_MESSAGE = (
    "A complaint draft is already in progress. Reset or start a New Complaint "
    "before submitting a different complaint. Your current draft was not changed."
)


def _updated_labels(patch: ComplaintPatch, exclude: set[ComplaintFieldKey] | None = None) -> str:
    skip = exclude or set()
    keys = [
        key.value if isinstance(key, ComplaintFieldKey) else str(key)
        for key in patch.changes
        if (key if isinstance(key, ComplaintFieldKey) else ComplaintFieldKey(key)) not in skip
    ]
    return join_field_labels(keys)


def new_complaint_message(
    *,
    source_patch: ComplaintPatch,
    assessment_ran: bool,
    status: ComplaintStatus,
    missing_required_fields: list[str],
    input_kind: str = "text",
) -> str:
    extracted = bool(source_patch.changes)
    from_document = input_kind == "document"

    if status == ComplaintStatus.READY_TO_COMMIT:
        if from_document:
            if assessment_ran:
                return (
                    "I extracted the complaint document and prepared an initial risk "
                    "assessment. The record is ready for QA review."
                )
            return (
                "I extracted the complaint document. The record is ready for QA review."
            )
        if assessment_ran:
            return (
                "I extracted the complaint and prepared an initial risk "
                "assessment. The record is ready for QA review."
            )
        return "I extracted the complaint. The record is ready for QA review."

    missing = join_field_labels(missing_required_fields)
    if extracted:
        prefix = (
            "I extracted the available complaint details from the document."
            if from_document
            else "I extracted the available complaint details."
        )
    else:
        prefix = (
            "I could not extract additional complaint details from the document."
            if from_document
            else "I could not extract additional complaint details from the message."
        )
    if missing:
        return f"{prefix} I still need: {missing} before this record can be ready for review."
    return prefix


def correction_message(
    *,
    correction_patch: ComplaintPatch,
    assessment_ran: bool,
    status: ComplaintStatus,
    missing_required_fields: list[str],
) -> str:
    updated = _updated_labels(correction_patch)
    if not updated:
        return (
            "I did not find an explicit field correction to apply. "
            "The complaint draft was not changed."
        )

    parts = [f"Updated {updated}."]
    if assessment_ran:
        parts.append("The risk assessment was refreshed")
        if status == ComplaintStatus.READY_TO_COMMIT:
            parts[-1] += " and the complaint is ready for review."
        else:
            parts[-1] += "."
            missing = join_field_labels(missing_required_fields)
            if missing:
                parts.append(f"I still need: {missing} before this record can be ready for review.")
    elif status == ComplaintStatus.READY_TO_COMMIT:
        parts.append("The complaint is ready for review.")
    else:
        missing = join_field_labels(missing_required_fields)
        if missing:
            parts.append(
                f"I still need: {missing} before this record can be ready for review."
            )
    return " ".join(parts)
