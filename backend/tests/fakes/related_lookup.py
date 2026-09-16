"""Fake related-complaint lookup for graph and API tests."""

from __future__ import annotations

import uuid

from app.domain.complaint import ComplaintFields, RelatedComplaintMatch
from app.services.related_complaint_service import RelatedComplaintLookupResult


class FakeRelatedComplaintLookup:
    def __init__(
        self,
        *,
        matches: list[RelatedComplaintMatch] | None = None,
        evaluated: bool = True,
        fail: bool = False,
    ) -> None:
        self.matches = matches or []
        self.evaluated = evaluated
        self.fail = fail
        self.calls = 0
        self.last_fields: ComplaintFields | None = None
        self.last_exclude_id: uuid.UUID | None = None

    def find_related(
        self,
        fields: ComplaintFields,
        *,
        exclude_id: uuid.UUID | None = None,
        limit: int = 3,
    ) -> RelatedComplaintLookupResult:
        self.calls += 1
        self.last_fields = fields
        self.last_exclude_id = exclude_id
        if self.fail:
            raise RuntimeError("history unavailable")
        del limit
        return RelatedComplaintLookupResult(
            evaluated=self.evaluated,
            matches=list(self.matches)[:3],
        )
