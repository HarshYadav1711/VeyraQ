"""Vercel Python entrypoint — re-exports the single FastAPI application.

Do not create a second FastAPI instance here. All middleware, routes,
CORS, and configuration live in app.main.
"""

from app.main import app

__all__ = ["app"]
