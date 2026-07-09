"""HTTP route for the user dashboard."""

import logging

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


@router.get("", response_model=DashboardResponse)
def get_dashboard(current_user: User = Depends(get_current_user)) -> DashboardResponse:
    """Return learning analytics and activity summary for the current user."""

    service = DashboardService(ActivityRepository())
    return service.build(current_user)
