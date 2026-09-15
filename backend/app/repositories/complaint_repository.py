import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.complaint import Complaint

HISTORY_LIMIT = 100


class ComplaintRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, complaint: Complaint) -> Complaint:
        self._session.add(complaint)
        self._session.commit()
        self._session.refresh(complaint)
        return complaint

    def rollback(self) -> None:
        self._session.rollback()

    def get_by_id(self, complaint_id: uuid.UUID) -> Complaint | None:
        return self._session.get(Complaint, complaint_id)

    def list_committed(self, *, limit: int = HISTORY_LIMIT) -> list[Complaint]:
        bounded = max(1, min(limit, HISTORY_LIMIT))
        statement = (
            select(Complaint)
            .order_by(Complaint.committed_at.desc())
            .limit(bounded)
        )
        return list(self._session.scalars(statement).all())

    def exists_complaint_number(self, complaint_number: str) -> bool:
        statement = select(Complaint.id).where(
            Complaint.complaint_number == complaint_number
        )
        return self._session.scalar(statement) is not None
