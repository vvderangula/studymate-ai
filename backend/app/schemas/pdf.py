"""Pydantic schemas for the PDF upload feature."""

from datetime import datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Metadata returned to the client after a successful PDF upload."""

    id: str
    filename: str
    original_name: str
    size: int
    upload_time: datetime
    status: str
    user_id: str | None = None


class ProcessResponse(BaseModel):
    """Result of processing a stored PDF into text chunks."""

    id: str
    processing_status: str
    processed_at: datetime | None = None
    page_count: int | None = None
    chunk_count: int | None = None


class ChatRequest(BaseModel):
    """A question asked about a previously processed PDF."""

    question: str


class Citation(BaseModel):
    """A source reference supporting a grounded answer."""

    page: int | None = None
    chunk_id: str
    source_reference: str


class ChatResponse(BaseModel):
    """An answer grounded in the PDF, with citations and metadata."""

    answer: str
    citations: list[Citation]
    metadata: dict
    conversation_id: str | None = None


class DocumentItem(BaseModel):
    """A PDF in the user's library, with its chat activity."""

    id: str
    original_name: str
    size: int
    upload_time: datetime
    processing_status: str
    processed_at: datetime | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    message_count: int = 0
    last_active: datetime


class DocumentsResponse(BaseModel):
    """Every PDF the user uploaded, most recently active first."""

    documents: list[DocumentItem]
