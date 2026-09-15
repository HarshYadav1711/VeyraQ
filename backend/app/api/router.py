from fastapi import APIRouter

from app.api.routes import assistant, complaints, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(complaints.router)
api_router.include_router(assistant.router)
