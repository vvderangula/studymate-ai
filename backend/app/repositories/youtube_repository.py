"""Repository for processed YouTube video metadata.

Records are per user: the same video can belong to several people, each with
their own record. The transcript vectors are shared (keyed by video id).
"""

from __future__ import annotations

from pymongo import DESCENDING

from app.core.database import Collections
from app.models.youtube import YoutubeMetadata
from app.repositories.base import MongoRepository, as_utc


class YoutubeMetadataRepository(MongoRepository):
    """The only component that reads or writes ``youtube_videos``.

    Pass ``user_id`` to scope every lookup to that user's records.
    """

    collection_name = Collections.VIDEOS

    def __init__(self, user_id: str | None = None, db=None) -> None:
        super().__init__(db)
        self._user_id = user_id

    def _scope(self, query: dict) -> dict:
        return {**query, "user_id": self._user_id} if self._user_id else query

    def upsert(self, record: YoutubeMetadata) -> None:
        """Insert or update the record for (user, video)."""

        self.collection.update_one(
            {"user_id": record.user_id, "video_id": record.video_id},
            {
                "$set": {
                    "url": record.url,
                    "title": record.title,
                    "duration": record.duration,
                    "thumbnail": record.thumbnail,
                    "processing_status": record.processing_status,
                    "processed_at": record.processed_at,
                    "chunk_count": record.chunk_count,
                },
                "$setOnInsert": {"created_at": record.created_at},
            },
            upsert=True,
        )

    def get(self, video_id: str) -> YoutubeMetadata | None:
        """Return a record for ``video_id`` (the scoped user's, if scoped)."""

        return _to_metadata(self.collection.find_one(self._scope({"video_id": video_id})))

    def list_processed(self) -> list[YoutubeMetadata]:
        """Completed videos, newest first (scoped if a user was given)."""

        cursor = self.collection.find(self._scope({"processing_status": "completed"})).sort(
            "processed_at", DESCENDING
        )
        return [_to_metadata(doc) for doc in cursor]

    def list_by_user(self, user_id: str) -> list[YoutubeMetadata]:
        """Completed videos owned by ``user_id``, newest first."""

        cursor = self.collection.find(
            {"processing_status": "completed", "user_id": user_id}
        ).sort("processed_at", DESCENDING)
        return [_to_metadata(doc) for doc in cursor]

    def delete(self, user_id: str, video_id: str) -> None:
        """Remove one user's record of a video."""

        self.collection.delete_one({"user_id": user_id, "video_id": video_id})


def _to_metadata(doc: dict | None) -> YoutubeMetadata | None:
    if doc is None:
        return None
    return YoutubeMetadata(
        video_id=doc["video_id"],
        url=doc["url"],
        title=doc["title"],
        duration=doc.get("duration"),
        thumbnail=doc.get("thumbnail"),
        created_at=as_utc(doc.get("created_at")),
        user_id=doc.get("user_id"),
        processing_status=doc.get("processing_status", "pending"),
        processed_at=as_utc(doc.get("processed_at")),
        chunk_count=doc.get("chunk_count"),
    )
