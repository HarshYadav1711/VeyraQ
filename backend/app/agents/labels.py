"""Central field labels for backend assistant messages. Keep aligned with the UI."""

from app.domain.complaint import ComplaintFieldKey

FIELD_LABELS: dict[str, str] = {
    ComplaintFieldKey.COMPLAINT_SOURCE.value: "Complaint Source",
    ComplaintFieldKey.CUSTOMER_NAME.value: "Customer Name",
    ComplaintFieldKey.PRODUCT_NAME.value: "Product Name",
    ComplaintFieldKey.PRODUCT_STRENGTH_GRADE.value: "Product Strength / Grade",
    ComplaintFieldKey.BATCH_LOT_NUMBER.value: "Batch / Lot Number",
    ComplaintFieldKey.AFFECTED_QUANTITY.value: "Affected Quantity",
    ComplaintFieldKey.MANUFACTURING_DATE.value: "Manufacturing Date",
    ComplaintFieldKey.EXPIRY_DATE.value: "Expiry Date",
    ComplaintFieldKey.COMPLAINT_DATE.value: "Complaint Date",
    ComplaintFieldKey.COMPLAINT_CATEGORY.value: "Complaint Type / Category",
    ComplaintFieldKey.COMPLAINT_DESCRIPTION.value: "Complaint Description",
    ComplaintFieldKey.ORIGINATING_SITE_BLOCK.value: "Originating Site Block",
    ComplaintFieldKey.IMPACTED_NON_PRODUCT_MATERIALS.value: (
        "Impacted Non-Product Materials"
    ),
    ComplaintFieldKey.INITIAL_SEVERITY.value: "Initial Severity",
    ComplaintFieldKey.PRIORITY.value: "Priority",
    ComplaintFieldKey.SUGGESTED_NEXT_ACTION.value: "Suggested Next Action",
    ComplaintFieldKey.INITIAL_RISK_ASSESSMENT.value: "Initial Risk Assessment",
}


def field_label(field_key: str) -> str:
    return FIELD_LABELS.get(field_key, field_key)


def join_field_labels(field_keys: list[str]) -> str:
    labels = [field_label(key) for key in field_keys]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"
