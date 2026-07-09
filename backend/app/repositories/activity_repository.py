"""Repository for persisting and querying user activity events."""

import sqlite3
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from app.core.database import connect
from app.models.activity import ActivityEntry


class ActivityRepository:
    """Data-access layer for the ``activity_log`` table.

    Provides logging of user events and aggregation queries for the
    dashboard. A connection factory is injected to keep the repository
    testable against an isolated database.
    """

    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection] = connect,
    ) -> None:
        self._connect = connection_factory

    def log(
        self,
        user_id: str,
        event_type: str,
        resource_id: str | None = None,
        resource_title: str | None = None,
    ) -> None:
        """Append a new activity entry for the given user."""

        entry_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO activity_log (id, user_id, event_type, resource_id, resource_title, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (entry_id, user_id, event_type, resource_id, resource_title, now),
            )
            connection.commit()
        finally:
            connection.close()

    def count_by_event_types(self, user_id: str) -> dict[str, int]:
        """Return a mapping of event_type → count for the given user."""

        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT event_type, COUNT(*) AS cnt
                FROM activity_log
                WHERE user_id = ?
                GROUP BY event_type
                """,
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

        return {row["event_type"]: row["cnt"] for row in rows}

    def get_recent(self, user_id: str, limit: int = 10) -> list[ActivityEntry]:
        """Return the most recent activity entries for the given user."""

        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT id, user_id, event_type, resource_id, resource_title, created_at
                FROM activity_log
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        finally:
            connection.close()

        return [_row_to_entry(row) for row in rows]

    def get_latest_by_event_type(
        self, user_id: str, event_type: str
    ) -> ActivityEntry | None:
        """Return the most recent entry for a specific event type, or ``None``."""

        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT id, user_id, event_type, resource_id, resource_title, created_at
                FROM activity_log
                WHERE user_id = ? AND event_type = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, event_type),
            ).fetchone()
        finally:
            connection.close()

        return _row_to_entry(row) if row else None

    def count_distinct_days(self, user_id: str) -> int:
        """Return the number of distinct calendar days with activity."""

        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT COUNT(DISTINCT substr(created_at, 1, 10)) AS cnt
                FROM activity_log
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        finally:
            connection.close()

        return row["cnt"] if row else 0


def _row_to_entry(row: sqlite3.Row) -> ActivityEntry:
    return ActivityEntry(
        id=row["id"],
        user_id=row["user_id"],
        event_type=row["event_type"],
        resource_id=row["resource_id"],
        resource_title=row["resource_title"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
