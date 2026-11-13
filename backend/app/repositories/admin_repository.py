"""Read-only reporting across all collections, for the admin pages."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from pymongo.database import Database

from app.core.database import Collections, get_db
from app.repositories.base import as_utc, utcnow


class AdminRepository:
    """Aggregate counts for the admin dashboard. Never writes."""

    def __init__(self, db: Database | None = None) -> None:
        self._db = db

    @property
    def db(self) -> Database:
        return self._db if self._db is not None else get_db()

    def totals(self) -> dict[str, int]:
        """Document counts per collection."""

        names = {
            "users": Collections.USERS,
            "pdfs": Collections.PDFS,
            "videos": Collections.VIDEOS,
            "conversations": Collections.CONVERSATIONS,
            "messages": Collections.MESSAGES,
            "quizzes": Collections.QUIZZES,
            "notes": Collections.NOTES,
            "searches": Collections.PAPER_SEARCHES,
            "saved_papers": Collections.SAVED_PAPERS,
        }
        return {key: self.db[name].count_documents({}) for key, name in names.items()}

    def daily(self, collection: str, days: int = 14) -> list[tuple[date, int]]:
        """Documents created per UTC day over the last ``days`` days (oldest first)."""

        start = (utcnow() - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        counts = Counter(
            as_utc(doc["created_at"]).date()
            for doc in self.db[collection].find(
                {"created_at": {"$gte": start}}, {"created_at": 1}
            )
        )
        first = start.date()
        return [(first + timedelta(days=i), counts.get(first + timedelta(days=i), 0)) for i in range(days)]

    def event_breakdown(self) -> dict[str, int]:
        """Activity events by type, across all users."""

        rows = self.db[Collections.ACTIVITY].aggregate(
            [{"$group": {"_id": "$event_type", "count": {"$sum": 1}}}]
        )
        return {row["_id"]: row["count"] for row in rows}

    def active_users(self, days: int) -> int:
        """Distinct users with any activity in the last ``days`` days."""

        since = utcnow() - timedelta(days=days)
        return len(
            self.db[Collections.ACTIVITY].distinct("user_id", {"created_at": {"$gte": since}})
        )

    def per_user(self, collection: str) -> dict[str, int]:
        """Document count per user_id in one collection."""

        rows = self.db[collection].aggregate(
            [{"$group": {"_id": "$user_id", "count": {"$sum": 1}}}]
        )
        return {row["_id"]: row["count"] for row in rows if row["_id"]}

    def last_active(self) -> dict[str, object]:
        """Latest activity time per user_id."""

        rows = self.db[Collections.ACTIVITY].aggregate(
            [{"$group": {"_id": "$user_id", "last": {"$max": "$created_at"}}}]
        )
        return {row["_id"]: as_utc(row["last"]) for row in rows if row["_id"]}

    def users(self) -> list[dict]:
        """All users, newest first (no password hashes)."""

        return list(
            self.db[Collections.USERS]
            .find({}, {"password_hash": 0})
            .sort("created_at", -1)
        )
