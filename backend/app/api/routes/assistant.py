"""Assistant process API: text and document complaint intelligence via LangGraph."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from app.agents.graph import (
    build_complaint_graph,
    build_initial_state,
    result_patch,
    result_related_complaints,
)
from app.agents.protocol import AIService
from app.db.session import get_db
from app.domain.complaint import (
    ASSISTANT_MESSAGE_MAX_LENGTH,
    ComplaintFields,
    ComplaintPatch,
    ComplaintStatus,
    RelatedComplaintMatch,
    is_complaint_fields_empty,
)
from app.services.ai_errors import AIServiceError
from app.services.complaint_service import ComplaintService
from app.services.document_limits import POPULATED_DRAFT_MESSAGE
from app.services.document_service import DocumentValidationError, extract_document
from app.services.groq_service import GroqService
from app.services.investigation_service import (
    InvestigationAssistanceResponse,
    InvestigationService,
    InvestigationValidationError,
    SAFE_INVESTIGATION_UNAVAILABLE,
)
from app.services.related_complaint_service import (
    RelatedComplaintLookup,
    RelatedComplaintService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])

SAFE_UNAVAILABLE_DETAIL = (
    "AI processing is temporarily unavailable. Your complaint draft has not been changed."
)


class AssistantProcessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=ASSISTANT_MESSAGE_MAX_LENGTH)
    fields: ComplaintFields

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    document_type: Literal["pdf", "txt", "eml"]


class AssistantProcessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal["new_complaint", "correction"]
    patch: ComplaintPatch
    status: Literal["needs_information", "ready_to_commit"]
    missing_required_fields: list[str]
    assistant_message: str
    warnings: list[str] = Field(default_factory=list)
    document: DocumentMetadata | None = None
    related_complaints: list[RelatedComplaintMatch] = Field(default_factory=list)
    related_lookup_evaluated: bool = False


def get_ai_service() -> AIService:
    return GroqService.from_settings()


def get_related_lookup(db: Session = Depends(get_db)) -> RelatedComplaintLookup:
    service = ComplaintService(db)
    return RelatedComplaintService(service.list_related_history)


def _response_from_graph_result(
    result: dict,
    *,
    document: DocumentMetadata | None = None,
) -> AssistantProcessResponse:
    target_status = result["target_status"]
    if target_status not in {
        ComplaintStatus.NEEDS_INFORMATION.value,
        ComplaintStatus.READY_TO_COMMIT.value,
    }:
        target_status = ComplaintStatus.NEEDS_INFORMATION.value

    intent = result["intent"] if result["intent"] == "correction" else "new_complaint"
    return AssistantProcessResponse(
        intent=intent,
        patch=result_patch(result),
        status=target_status,
        missing_required_fields=result["missing_required_fields"],
        assistant_message=result["assistant_message"],
        warnings=result["warnings"],
        document=document,
        related_complaints=result_related_complaints(result),
        related_lookup_evaluated=bool(result.get("related_lookup_evaluated", False)),
    )


def _parse_current_fields(raw: str) -> ComplaintFields:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="current_fields must be valid JSON.",
        ) from exc
    try:
        return ComplaintFields.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="current_fields must match the complaint field contract.",
        ) from exc


@router.post(
    "/process",
    response_model=AssistantProcessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "AI processing unavailable",
        },
    },
)
def process_assistant_message(
    request: AssistantProcessRequest,
    ai_service: AIService = Depends(get_ai_service),
    related_lookup: RelatedComplaintLookup = Depends(get_related_lookup),
) -> AssistantProcessResponse:
    request_id = str(uuid.uuid4())
    logger.info(
        "assistant.process start request_id=%s model=%s",
        request_id,
        getattr(ai_service, "model_id", "unknown"),
    )
    graph = build_complaint_graph(ai_service, related_lookup)
    try:
        result = graph.invoke(
            build_initial_state(
                user_message=request.message,
                fields=request.fields,
                request_id=request_id,
                input_kind="text",
            )
        )
    except AIServiceError:
        logger.info("assistant.process failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SAFE_UNAVAILABLE_DETAIL,
        ) from None

    logger.info("assistant.process success request_id=%s", request_id)
    return _response_from_graph_result(result)


@router.post(
    "/process-document",
    response_model=AssistantProcessResponse,
    responses={
        status.HTTP_409_CONFLICT: {"description": "Draft already populated"},
        status.HTTP_413_CONTENT_TOO_LARGE: {"description": "Upload too large"},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"description": "Unsupported file type"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "AI processing unavailable"},
    },
)
async def process_assistant_document(
    file: UploadFile = File(...),
    current_fields: str = Form(...),
    ai_service: AIService = Depends(get_ai_service),
    related_lookup: RelatedComplaintLookup = Depends(get_related_lookup),
) -> AssistantProcessResponse:
    request_id = str(uuid.uuid4())
    fields = _parse_current_fields(current_fields)

    if not is_complaint_fields_empty(fields):
        logger.info(
            "assistant.process_document conflict request_id=%s",
            request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=POPULATED_DRAFT_MESSAGE,
        )

    file_bytes = await file.read()
    try:
        extracted = extract_document(
            filename=file.filename,
            content_type=file.content_type,
            file_bytes=file_bytes,
        )
    except DocumentValidationError as exc:
        logger.info(
            "assistant.process_document validation_failed request_id=%s status=%s type=%s bytes=%s",
            request_id,
            exc.status_code,
            (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else "unknown",
            len(file_bytes),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None

    logger.info(
        "assistant.process_document start request_id=%s type=%s bytes=%s pages=%s model=%s",
        request_id,
        extracted.document_type,
        extracted.byte_size,
        extracted.page_count,
        getattr(ai_service, "model_id", "unknown"),
    )

    graph = build_complaint_graph(ai_service, related_lookup)
    try:
        result = graph.invoke(
            build_initial_state(
                user_message=extracted.text,
                fields=fields,
                request_id=request_id,
                input_kind="document",
            )
        )
    except AIServiceError:
        logger.info("assistant.process_document failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SAFE_UNAVAILABLE_DETAIL,
        ) from None

    logger.info("assistant.process_document success request_id=%s", request_id)
    return _response_from_graph_result(
        result,
        document=DocumentMetadata(
            filename=extracted.filename,
            document_type=extracted.document_type,
        ),
    )


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: ComplaintFields


@router.post(
    "/investigation",
    response_model=InvestigationAssistanceResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Insufficient complaint context",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Investigation assistance unavailable",
        },
    },
)
def generate_investigation_assistance(
    request: InvestigationRequest,
    ai_service: AIService = Depends(get_ai_service),
    related_lookup: RelatedComplaintLookup = Depends(get_related_lookup),
) -> InvestigationAssistanceResponse:
    """On-demand derived analysis. Does not mutate complaint fields or status."""
    request_id = str(uuid.uuid4())
    logger.info(
        "assistant.investigation start request_id=%s model=%s",
        request_id,
        getattr(ai_service, "model_id", "unknown"),
    )
    service = InvestigationService(ai_service, related_lookup)
    try:
        result = service.generate(request.fields)
    except InvestigationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.message,
        ) from None
    except AIServiceError:
        logger.info("assistant.investigation failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SAFE_INVESTIGATION_UNAVAILABLE,
        ) from None

    logger.info(
        "assistant.investigation success request_id=%s related_used=%s hypotheses=%s capa=%s",
        request_id,
        result.related_history_used,
        len(result.root_cause_hypotheses),
        len(result.capa_suggestions),
    )
    return result
