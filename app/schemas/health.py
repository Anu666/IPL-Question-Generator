# Health schema
# Defines the structured Pydantic response model returned by the /health endpoint.

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str          # "ok" when the service is healthy
    version: str         # Application version from settings
    app_name: str        # Human-readable application name
