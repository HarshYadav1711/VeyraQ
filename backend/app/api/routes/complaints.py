import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.complaint import (
    CommitValidationError,
    ComplaintCommitRequest,
    ComplaintListItem,
    CommittedComplaintResponse,
)
from app.services.complaint_service import (
    CommitValidationException,
    ComplaintService,
    PersistenceException,
)

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post(
    "/commit",
    response_model=CommittedComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": CommitValidationError},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Persistence unavailable",
        },
    },
)
def commit_complaint(
    request: ComplaintCommitRequest,
    db: Session = Depends(get_db),
) -> CommittedComplaintResponse:
    service = ComplaintService(db)
    try:
        return service.commit(request)
    except CommitValidationException as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Complaint is missing required fields for commit",
                "missing_fields": exc.missing_fields,
            },
        ) from None
    except PersistenceException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"detail": "Unable to persist complaint"},
        ) from None


@router.get("", response_model=list[ComplaintListItem])
def list_complaints(
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ComplaintListItem]:
    return ComplaintService(db).list_history(limit=limit)


@router.get("/{complaint_id}", response_model=CommittedComplaintResponse)
def get_complaint(
    complaint_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CommittedComplaintResponse:
    result = ComplaintService(db).get(complaint_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Complaint not found"},
        )
    return result
