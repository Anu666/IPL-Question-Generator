# Application entry point
# Initializes the FastAPI app, registers routers, and configures middleware.
# Run with: uvicorn app.main:app --reload

from fastapi import FastAPI

from app.api.v1.routes import router as v1_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount the v1 router — all routes defined there become /api/v1/<path>
app.include_router(v1_router, prefix="/api/v1")
