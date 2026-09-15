from fastapi import APIRouter

from app.api.routes import complaints, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(complaints.router)
