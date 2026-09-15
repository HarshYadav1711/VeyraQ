from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.session import check_database_connection

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str


class ReadinessResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="veyraq-api")


@router.get(
    "/readiness",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse},
    },
)
def readiness() -> ReadinessResponse | JSONResponse:
    if check_database_connection():
        return ReadinessResponse(status="ready", database="connected")

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unavailable", "database": "disconnected"},
    )
