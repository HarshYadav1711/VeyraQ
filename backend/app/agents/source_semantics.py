"""Semantic validation for source extraction (beyond evidence grounding)."""

from app.agents.grounding import normalize_whitespace


def complaint_source_duplicates_customer_name(
    complaint_source: str | None,
    customer_name: str | None,
) -> bool:
    """True when complaint_source is merely a copy of the customer proper name."""
    if complaint_source is None or customer_name is None:
        return False
    source = normalize_whitespace(complaint_source).lower()
    customer = normalize_whitespace(customer_name).lower()
    if not source or not customer:
        return False
    return source == customer
