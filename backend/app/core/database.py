"""MongoDB connection and collection setup.

Owns the single shared ``MongoClient`` and the index definitions. Higher
layers access data only through repositories (``app/repositories``), never
through this module directly.
"""

from __future__ import annotations

import logging

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from app.core.config import settings

logger = logging.getLogger(__name__)


class Collections:
    """Collection names, in one place."""

    USERS = "users"
    ACTIVITY = "activity_log"
    PDFS = "pdf_documents"
    VIDEOS = "youtube_videos"
    CHUNKS = "chunks"
    CONVERSATIONS = "conversations"
    MESSAGES = "messages"
    QUIZZES = "quizzes"
    NOTES = "notes"
    PAPER_SEARCHES = "paper_searches"
    SAVED_PAPERS = "saved_papers"


_client: MongoClient | None = None
_override: Database | None = None


def get_db() -> Database:
    """Return the application database, connecting on first use."""

    global _client
    if _override is not None:
        return _override
    if _client is None:
        if not settings.mongodb_uri:
            raise RuntimeError(
                "MONGODB_URI is not set. Add your MongoDB connection string to backend/.env."
            )
        _client = MongoClient(
            settings.mongodb_uri,
            tz_aware=True,
            serverSelectionTimeoutMS=10_000,
            appname="studymate-ai",
        )
    return _client.get_default_database(default=settings.mongodb_db)


def use_database(database: Database | None) -> None:
    """Point the app at another database (tests use an in-memory one)."""

    global _override
    _override = database


def init_db() -> None:
    """Create indexes. Idempotent; safe to run on every start."""

    db = get_db()
    db[Collections.USERS].create_index("email", unique=True)

    db[Collections.ACTIVITY].create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db[Collections.ACTIVITY].create_index([("user_id", ASCENDING), ("event_type", ASCENDING)])

    db[Collections.PDFS].create_index([("user_id", ASCENDING), ("upload_time", DESCENDING)])

    # One record per user per video: two people can study the same video.
    db[Collections.VIDEOS].create_index(
        [("user_id", ASCENDING), ("video_id", ASCENDING)], unique=True
    )
    db[Collections.VIDEOS].create_index("video_id")

    db[Collections.CHUNKS].create_index(
        [("source_id", ASCENDING), ("index", ASCENDING)], unique=True
    )

    db[Collections.CONVERSATIONS].create_index(
        [("user_id", ASCENDING), ("kind", ASCENDING), ("updated_at", DESCENDING)]
    )
    db[Collections.CONVERSATIONS].create_index(
        [("user_id", ASCENDING), ("kind", ASCENDING), ("source_id", ASCENDING)]
    )
    db[Collections.MESSAGES].create_index(
        [("conversation_id", ASCENDING), ("created_at", ASCENDING)]
    )

    for name in (Collections.QUIZZES, Collections.NOTES, Collections.PAPER_SEARCHES):
        db[name].create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])

    db[Collections.SAVED_PAPERS].create_index(
        [("user_id", ASCENDING), ("paper_id", ASCENDING)], unique=True
    )
    db[Collections.SAVED_PAPERS].create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])

    logger.info("MongoDB ready (database '%s')", db.name)
