"""Centralized related-complaint matching configuration.

Deterministic recurrence / related-history signals only.
Does not prove literal duplicates — a human decides the relationship.
"""

from __future__ import annotations

from app.domain.complaint import ComplaintFieldKey

# Weighted contribution to the composite score (must sum to 1.00).
BATCH_MATCH_WEIGHT = 0.35
PRODUCT_MATCH_WEIGHT = 0.25
CATEGORY_MATCH_WEIGHT = 0.15
DESCRIPTION_SIMILARITY_WEIGHT = 0.20
CUSTOMER_MATCH_WEIGHT = 0.05

RELATED_COMPLAINT_THRESHOLD = 0.60
STRONG_MATCH_THRESHOLD = 0.80

MAX_RELATED_RESULTS = 3
MAX_HISTORY_CANDIDATES = 100

# Description similarity blend.
DESCRIPTION_JACCARD_WEIGHT = 0.6
DESCRIPTION_SEQUENCE_WEIGHT = 0.4

# Tiny explicit stopword set for description tokens (stdlib only).
DESCRIPTION_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "on",
        "in",
        "to",
        "for",
        "by",
        "from",
        "with",
        "was",
        "were",
        "is",
        "are",
        "been",
        "be",
        "this",
        "that",
        "it",
        "as",
        "at",
        "multiple",
        "several",
    }
)

# Correction fields that require related-history re-evaluation.
RELATED_MATCH_FIELDS: frozenset[ComplaintFieldKey] = frozenset(
    {
        ComplaintFieldKey.PRODUCT_NAME,
        ComplaintFieldKey.BATCH_LOT_NUMBER,
        ComplaintFieldKey.COMPLAINT_CATEGORY,
        ComplaintFieldKey.COMPLAINT_DESCRIPTION,
        ComplaintFieldKey.CUSTOMER_NAME,
    }
)
