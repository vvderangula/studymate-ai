"""Repository for the user activity log (dashboard analytics)."""

from __future__ import annotations

import uuid

from pymongo import DESCENDING

from app.core.database import Collections
from app.models.activity import ActivityEntry
from app.repositories.base import MongoRepository, as_utc, utcnow


class ActivityRepository(MongoRepository):
    """The only component that reads or writes ``activity_log``."""

    collection_name = Collections.ACTIVITY

    def log(
        self,
        user_id: str,
        event_type: str,
        resource_id: str | None = None,
        resource_title: str | None = None,
    ) -> None:
        """Append an activity entry for ``user_id``."""

        self.collection.insert_one(
            {
                "_id": uuid.uuid4().hex,
                "user_id": user_id,
                "event_type": event_type,
                "resource_id": resource_id,
                "resource_title": resource_title,
                "created_at": utcnow(),
            }
        )

    def count_by_event_types(self, user_id: str) -> dict[str, int]:
        """Mapping of event_type to count for ``user_id``."""

        rows = self.collection.aggregate(
            [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
            ]
        )
        return {row["_id"]: row["count"] for row in rows}

    def get_recent(self, user_id: str, limit: int = 10) -> list[ActivityEntry]:
        """Most recent entries for ``user_id``."""

        cursor = (
            self.collection.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return [_to_entry(doc) for doc in cursor]

    def get_latest_by_event_type(self, user_id: str, event_type: str) -> ActivityEntry | None:
        """Most recent entry of one type, or ``None``."""

        doc = self.collection.find_one(
            {"user_id": user_id, "event_type": event_type},
            sort=[("created_at", DESCENDING)],
        )
        return _to_entry(doc) if doc else None

    def count_distinct_days(self, user_id: str) -> int:
        """Number of distinct UTC calendar days with activity."""

        days = {
            as_utc(doc["created_at"]).date()
            for doc in self.collection.find({"user_id": user_id}, {"created_at": 1})
        }
        return len(days)


def _to_entry(doc: dict) -> ActivityEntry:
    return ActivityEntry(
        id=doc["_id"],
        user_id=doc["user_id"],
        event_type=doc["event_type"],
        resource_id=doc.get("resource_id"),
        resource_title=doc.get("resource_title"),
        created_at=as_utc(doc["created_at"]),
    )
