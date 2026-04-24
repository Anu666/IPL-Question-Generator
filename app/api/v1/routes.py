# API v1 routes
# All v1 endpoints are registered on this router.
# The router is mounted in main.py under the /api/v1 prefix.

from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health_service import get_health

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["Health"],
)
def health_check():
    """Returns the current health status of the API."""
    return get_health()
