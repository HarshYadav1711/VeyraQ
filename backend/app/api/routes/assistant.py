"""Assistant process API: text complaint intelligence via LangGraph."""

from __future__ import annotations

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agents.graph import build_complaint_graph, build_initial_state, result_patch
from app.agents.protocol import AIService
from app.domain.complaint import (
    ASSISTANT_MESSAGE_MAX_LENGTH,
    ComplaintFields,
    ComplaintPatch,
    ComplaintStatus,
)
from app.services.ai_errors import AIServiceError
from app.services.groq_service import GroqService

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


class AssistantProcessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal["new_complaint", "correction"]
    patch: ComplaintPatch
    status: Literal["needs_information", "ready_to_commit"]
    missing_required_fields: list[str]
    assistant_message: str
    warnings: list[str] = Field(default_factory=list)


def get_ai_service() -> AIService:
    return GroqService.from_settings()


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
) -> AssistantProcessResponse:
    request_id = str(uuid.uuid4())
    logger.info(
        "assistant.process start request_id=%s model=%s",
        request_id,
        getattr(ai_service, "model_id", "unknown"),
    )
    graph = build_complaint_graph(ai_service)
    try:
        result = graph.invoke(
            build_initial_state(
                user_message=request.message,
                fields=request.fields,
                request_id=request_id,
            )
        )
    except AIServiceError:
        logger.info("assistant.process failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SAFE_UNAVAILABLE_DETAIL,
        ) from None

    target_status = result["target_status"]
    if target_status not in {
        ComplaintStatus.NEEDS_INFORMATION.value,
        ComplaintStatus.READY_TO_COMMIT.value,
    }:
        target_status = ComplaintStatus.NEEDS_INFORMATION.value

    intent = result["intent"] if result["intent"] == "correction" else "new_complaint"
    logger.info("assistant.process success request_id=%s", request_id)
    return AssistantProcessResponse(
        intent=intent,
        patch=result_patch(result),
        status=target_status,
        missing_required_fields=result["missing_required_fields"],
        assistant_message=result["assistant_message"],
        warnings=result["warnings"],
    )
