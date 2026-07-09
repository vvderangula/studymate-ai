"""Repository for persisting and retrieving YouTube video metadata."""

import sqlite3
from collections.abc import Callable
from datetime import datetime

from app.core.database import connect
from app.models.youtube import YoutubeMetadata


class YoutubeMetadataRepository:
    """Data-access layer for ``youtube_videos``.

    This is the only component permitted to read from or write to the
    YouTube metadata table. A connection factory is injected to keep the
    repository testable against an isolated database.
    """

    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection] = connect,
    ) -> None:
        self._connect = connection_factory

    def upsert(self, record: YoutubeMetadata) -> None:
        """Insert a new video record or replace an existing one."""

        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO youtube_videos (
                    video_id, url, title, duration, thumbnail, created_at,
                    user_id, processing_status, processed_at, chunk_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    url = excluded.url,
                    title = excluded.title,
                    duration = excluded.duration,
                    thumbnail = excluded.thumbnail,
                    user_id = COALESCE(youtube_videos.user_id, excluded.user_id),
                    processing_status = excluded.processing_status,
                    processed_at = excluded.processed_at,
                    chunk_count = excluded.chunk_count
                """,
                (
                    record.video_id,
                    record.url,
                    record.title,
                    record.duration,
                    record.thumbnail,
                    record.created_at.isoformat() if record.created_at else None,
                    record.user_id,
                    record.processing_status,
                    record.processed_at.isoformat() if record.processed_at else None,
                    record.chunk_count,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def get(self, video_id: str) -> YoutubeMetadata | None:
        """Return the metadata for ``video_id``, or ``None`` if not found."""

        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT video_id, url, title, duration, thumbnail, created_at,
                       user_id, processing_status, processed_at, chunk_count
                FROM youtube_videos
                WHERE video_id = ?
                """,
                (video_id,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            return None
        return _row_to_metadata(row)

    def list_processed(self) -> list[YoutubeMetadata]:
        """Return all videos whose processing has completed, newest first."""

        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT video_id, url, title, duration, thumbnail, created_at,
                       user_id, processing_status, processed_at, chunk_count
                FROM youtube_videos
                WHERE processing_status = 'completed'
                ORDER BY processed_at DESC
                """
            ).fetchall()
        finally:
            connection.close()

        return [_row_to_metadata(row) for row in rows]

    def list_by_user(self, user_id: str) -> list[YoutubeMetadata]:
        """Return completed videos owned by the given user, newest first."""

        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT video_id, url, title, duration, thumbnail, created_at,
                       user_id, processing_status, processed_at, chunk_count
                FROM youtube_videos
                WHERE processing_status = 'completed' AND user_id = ?
                ORDER BY processed_at DESC
                """,
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

        return [_row_to_metadata(row) for row in rows]


def _row_to_metadata(row: sqlite3.Row) -> YoutubeMetadata:
    """Map a database row to a :class:`YoutubeMetadata` instance."""

    created_at = row["created_at"]
    processed_at = row["processed_at"]
    return YoutubeMetadata(
        video_id=row["video_id"],
        url=row["url"],
        title=row["title"],
        duration=row["duration"],
        thumbnail=row["thumbnail"],
        created_at=datetime.fromisoformat(created_at) if created_at else None,
        user_id=row["user_id"],
        processing_status=row["processing_status"],
        processed_at=datetime.fromisoformat(processed_at) if processed_at else None,
        chunk_count=row["chunk_count"],
    )
