"""Domain models for the YouTube module."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class YoutubeMetadata:
    """Metadata describing a processed YouTube video.

    Attributes:
        video_id: The YouTube video identifier (also the vector-store key).
        url: The original YouTube URL submitted by the user.
        title: The video title.
        duration: Approximate video length in seconds, if known.
        thumbnail: URL of the video thumbnail image, if known.
        created_at: Timestamp when the video was first submitted.
        processing_status: Processing lifecycle state ("pending",
            "processing", "completed", or "failed").
        processed_at: Timestamp when processing last finished, if any.
        chunk_count: Number of transcript chunks produced, if processed.
    """

    video_id: str
    url: str
    title: str
    duration: int | None = None
    thumbnail: str | None = None
    created_at: datetime | None = None
    user_id: str | None = None
    processing_status: str = "pending"
    processed_at: datetime | None = None
    chunk_count: int | None = None
