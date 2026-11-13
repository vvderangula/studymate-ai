"""Admin-only routes: platform stats and the user list.

Every route depends on ``require_admin``: only accounts whose email is in
ADMIN_EMAILS can call them; everyone else gets 403.
"""

from fastapi import APIRouter, Depends

from app.core.auth import require_admin
from app.core.config import settings
from app.core.database import Collections
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.repositories.base import as_utc
from app.schemas.admin import AdminStats, AdminUser, DailyCount

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=AdminStats)
def stats(_: User = Depends(require_admin)) -> AdminStats:
    """Totals, active users, 14-day sign-ups and activity, and event mix."""

    report = AdminRepository()
    return AdminStats(
        totals=report.totals(),
        active_users_7d=report.active_users(7),
        active_users_30d=report.active_users(30),
        signups_daily=[DailyCount(day=d, count=c) for d, c in report.daily(Collections.USERS)],
        activity_daily=[DailyCount(day=d, count=c) for d, c in report.daily(Collections.ACTIVITY)],
        events=report.event_breakdown(),
    )


@router.get("/users", response_model=list[AdminUser])
def users(_: User = Depends(require_admin)) -> list[AdminUser]:
    """Every user with what they have stored, newest sign-up first."""

    report = AdminRepository()
    pdfs = report.per_user(Collections.PDFS)
    videos = report.per_user(Collections.VIDEOS)
    conversations = report.per_user(Collections.CONVERSATIONS)
    quizzes = report.per_user(Collections.QUIZZES)
    notes = report.per_user(Collections.NOTES)
    searches = report.per_user(Collections.PAPER_SEARCHES)
    last_active = report.last_active()

    return [
        AdminUser(
            id=doc["_id"],
            full_name=doc.get("full_name", ""),
            email=doc.get("email", ""),
            role=settings.role_for(doc.get("email", "")),
            created_at=as_utc(doc["created_at"]),
            last_active=last_active.get(doc["_id"]),
            pdfs=pdfs.get(doc["_id"], 0),
            videos=videos.get(doc["_id"], 0),
            conversations=conversations.get(doc["_id"], 0),
            quizzes=quizzes.get(doc["_id"], 0),
            notes=notes.get(doc["_id"], 0),
            searches=searches.get(doc["_id"], 0),
        )
        for doc in report.users()
    ]
