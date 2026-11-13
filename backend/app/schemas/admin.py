"""Pydantic schemas for the admin pages."""

from datetime import date, datetime

from pydantic import BaseModel


class DailyCount(BaseModel):
    day: date
    count: int


class AdminStats(BaseModel):
    """Platform-wide numbers for the admin overview."""

    totals: dict[str, int]
    active_users_7d: int
    active_users_30d: int
    signups_daily: list[DailyCount]
    activity_daily: list[DailyCount]
    events: dict[str, int]


class AdminUser(BaseModel):
    """One user as listed for admins."""

    id: str
    full_name: str
    email: str
    role: str
    created_at: datetime
    last_active: datetime | None = None
    pdfs: int = 0
    videos: int = 0
    conversations: int = 0
    quizzes: int = 0
    notes: int = 0
    searches: int = 0
