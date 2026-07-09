"""Health check endpoint used to verify the service is running."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str
    app_name: str
    environment: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return the current service status.

    Used by monitoring tools, load balancers, and Docker health checks.
    """

    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
    )
