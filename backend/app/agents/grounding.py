"""Deterministic evidence and correction-value grounding."""

import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_whitespace(value)
    return normalized or None


def is_span_in_text(span: str, source_text: str) -> bool:
    needle = normalize_whitespace(span).lower()
    haystack = normalize_whitespace(source_text).lower()
    if not needle:
        return False
    return needle in haystack


def can_ground_extracted_fact(value: str | None, evidence: str | None, source_text: str) -> bool:
    if value is None:
        return False
    if evidence is None or normalize_whitespace(evidence) == "":
        return False
    return is_span_in_text(evidence, source_text)
