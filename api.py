"""Compatibility entry point for the FastAPI service.

Run the API with ``uvicorn api:app``.
"""

from api_routes import app

__all__ = ["app"]
