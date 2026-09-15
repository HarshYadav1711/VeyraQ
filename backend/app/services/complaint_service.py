import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.complaint import Complaint
from app.domain.complaint import (
    REQUIRED_COMMIT_FIELDS,
    ComplaintCommitRequest,
    ComplaintFieldKey,
    ComplaintFieldValue,
    ComplaintFields,
    ComplaintListItem,
    ComplaintStatus,
    CommittedComplaintResponse,
    FieldProvenance,
)
from app.repositories.complaint_repository import HISTORY_LIMIT, ComplaintRepository


class CommitValidationException(Exception):
    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        super().__init__("Complaint is missing required fields for commit")


class PersistenceException(Exception):
    """Safe wrapper for unexpected database failures."""


def generate_complaint_number() -> str:
    """Assessment-only numbering. A real QMS would use a controlled sequence."""
    year = datetime.now(timezone.utc).year
    suffix = uuid.uuid4().hex[:6].upper()
    return f"CMP-{year}-{suffix}"


def _field_value(fields: ComplaintFields, key: ComplaintFieldKey) -> ComplaintFieldValue:
    return getattr(fields, key.value)


def find_missing_required_fields(fields: ComplaintFields) -> list[str]:
    missing: list[str] = []
    for key in REQUIRED_COMMIT_FIELDS:
        value = _field_value(fields, key).value
        if value is None or not value.strip():
            missing.append(key.value)
    return missing


def _build_field_metadata(fields: ComplaintFields) -> dict[str, dict[str, object | None]]:
    metadata: dict[str, dict[str, object | None]] = {}
    for key in ComplaintFieldKey:
        field = _field_value(fields, key)
        metadata[key.value] = {
            "provenance": field.provenance.value,
            "confidence": field.confidence,
            "evidence": field.evidence,
        }
    return metadata


def _column_values(fields: ComplaintFields) -> dict[str, str | None]:
    values: dict[str, str | None] = {}
    for key in ComplaintFieldKey:
        values[key.value] = _field_value(fields, key).value
    return values


def complaint_to_fields(complaint: Complaint) -> ComplaintFields:
    metadata = complaint.field_metadata or {}
    payload: dict[str, ComplaintFieldValue] = {}
    for key in ComplaintFieldKey:
        raw_meta = metadata.get(key.value, {})
        value = getattr(complaint, key.value)
        provenance_raw = raw_meta.get("provenance")
        if value is None:
            provenance = FieldProvenance.MISSING
        elif provenance_raw in {p.value for p in FieldProvenance}:
            provenance = FieldProvenance(provenance_raw)
            if provenance == FieldProvenance.MISSING:
                provenance = FieldProvenance.USER
        else:
            provenance = FieldProvenance.USER
        payload[key.value] = ComplaintFieldValue(
            value=value,
            provenance=provenance,
            confidence=raw_meta.get("confidence"),
            evidence=raw_meta.get("evidence"),
        )
    return ComplaintFields.model_validate(payload)


def complaint_to_response(complaint: Complaint) -> CommittedComplaintResponse:
    return CommittedComplaintResponse(
        id=complaint.id,
        complaint_number=complaint.complaint_number,
        status=ComplaintStatus.COMMITTED,
        fields=complaint_to_fields(complaint),
        created_at=complaint.created_at,
        committed_at=complaint.committed_at,
    )


def complaint_to_list_item(complaint: Complaint) -> ComplaintListItem:
    return ComplaintListItem(
        id=complaint.id,
        complaint_number=complaint.complaint_number,
        status=ComplaintStatus.COMMITTED,
        customer_name=complaint.customer_name,
        product_name=complaint.product_name,
        batch_lot_number=complaint.batch_lot_number,
        complaint_category=complaint.complaint_category,
        committed_at=complaint.committed_at,
    )


class ComplaintService:
    def __init__(self, session: Session) -> None:
        self._repo = ComplaintRepository(session)

    def commit(self, request: ComplaintCommitRequest) -> CommittedComplaintResponse:
        missing = find_missing_required_fields(request.fields)
        if missing:
            raise CommitValidationException(missing)

        now = datetime.now(timezone.utc)
        values = _column_values(request.fields)
        complaint = Complaint(
            id=uuid.uuid4(),
            complaint_number=generate_complaint_number(),
            field_metadata=_build_field_metadata(request.fields),
            created_at=now,
            committed_at=now,
            **values,
        )

        try:
            saved = self._repo.add(complaint)
        except IntegrityError as exc:
            self._repo.rollback()
            raise PersistenceException("Unable to persist complaint") from exc
        except SQLAlchemyError as exc:
            self._repo.rollback()
            raise PersistenceException("Unable to persist complaint") from exc

        return complaint_to_response(saved)

    def get(self, complaint_id: uuid.UUID) -> CommittedComplaintResponse | None:
        complaint = self._repo.get_by_id(complaint_id)
        if complaint is None:
            return None
        return complaint_to_response(complaint)

    def list_history(self, *, limit: int = HISTORY_LIMIT) -> list[ComplaintListItem]:
        return [complaint_to_list_item(item) for item in self._repo.list_committed(limit=limit)]
