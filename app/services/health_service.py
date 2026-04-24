# Health service
# Contains the business logic for the health check.
# Keeping logic here (rather than in the route) keeps routes thin
# and makes the service independently testable.

from app.core.config import settings
from app.schemas.health import HealthResponse


def get_health() -> HealthResponse:
    """Return the current health status of the application."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        app_name=settings.APP_NAME,
    )
