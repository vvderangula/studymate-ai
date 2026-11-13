"""Shared plumbing for MongoDB repositories."""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.collection import Collection
from pymongo.database import Database

from app.core.database import get_db


class MongoRepository:
    """Base class: one repository wraps one collection.

    The database is resolved lazily so repositories can be created at import
    time, and an explicit ``db`` can be injected in tests.
    """

    collection_name: str = ""

    def __init__(self, db: Database | None = None) -> None:
        self._db = db

    @property
    def collection(self) -> Collection:
        return (self._db if self._db is not None else get_db())[self.collection_name]


def utcnow() -> datetime:
    """Current time, timezone-aware UTC."""

    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """Mongo drivers may hand back naive UTC datetimes; make them aware."""

    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
