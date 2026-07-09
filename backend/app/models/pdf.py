"""Domain models for the PDF module."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PdfMetadata:
    """Metadata describing a stored PDF document.

    Attributes:
        id: Unique identifier (UUID hex) for the document.
        filename: Name of the file as stored on disk.
        original_name: Original filename provided by the uploader.
        size: File size in bytes.
        upload_time: Timestamp when the file was uploaded.
        status: Lifecycle status of the document (e.g. "uploaded").
        user_id: Owning user identifier, or ``None`` until auth exists.
        processing_status: Processing lifecycle state ("pending",
            "processing", "completed", or "failed").
        processed_at: Timestamp when processing last finished, if any.
        page_count: Number of pages with extractable text, if processed.
        chunk_count: Number of text chunks produced, if processed.
    """

    id: str
    filename: str
    original_name: str
    size: int
    upload_time: datetime
    status: str
    user_id: str | None = None
    processing_status: str = "pending"
    processed_at: datetime | None = None
    page_count: int | None = None
    chunk_count: int | None = None
