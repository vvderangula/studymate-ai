"""Pydantic schemas for the Learn from YouTube feature."""

from datetime import datetime

from pydantic import BaseModel


class ProcessYoutubeRequest(BaseModel):
    """A request to process a YouTube video by its URL."""

    url: str


class VideoItem(BaseModel):
    """A processed video in the user's library, with its chat activity."""

    video_id: str
    url: str
    title: str
    duration: int | None = None
    thumbnail: str | None = None
    processed_at: datetime | None = None
    chunk_count: int | None = None
    message_count: int = 0
    last_active: datetime


class VideosResponse(BaseModel):
    """The user's processed videos, most recently active first."""

    videos: list[VideoItem]


class YoutubeProcessResponse(BaseModel):
    """Result of retrieving and processing a YouTube transcript."""

    video_id: str
    title: str
    duration: int | None = None
    thumbnail: str | None = None
    processing_status: str
    processed_at: datetime | None = None
    chunk_count: int | None = None
