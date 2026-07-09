"""Repository for persisting and retrieving PDF document metadata."""

import sqlite3
from collections.abc import Callable
from datetime import datetime

from app.core.database import connect
from app.models.pdf import PdfMetadata


class PdfMetadataRepository:
    """Data-access layer for ``pdf_documents``.

    This is the only component permitted to read from or write to the
    PDF metadata table. A connection factory is injected to keep the
    repository testable against an isolated database.
    """

    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection] = connect,
    ) -> None:
        self._connect = connection_factory

    def create(self, record: PdfMetadata) -> None:
        """Insert a new PDF metadata record."""

        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO pdf_documents (
                    id, filename, original_name, size, upload_time, status,
                    user_id, processing_status, processed_at, page_count, chunk_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.filename,
                    record.original_name,
                    record.size,
                    record.upload_time.isoformat(),
                    record.status,
                    record.user_id,
                    record.processing_status,
                    record.processed_at.isoformat() if record.processed_at else None,
                    record.page_count,
                    record.chunk_count,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def update_processing(
        self,
        file_id: str,
        *,
        processing_status: str,
        processed_at: datetime | None = None,
        page_count: int | None = None,
        chunk_count: int | None = None,
    ) -> None:
        """Update the processing fields for a stored PDF."""

        connection = self._connect()
        try:
            connection.execute(
                """
                UPDATE pdf_documents
                SET processing_status = ?,
                    processed_at = ?,
                    page_count = ?,
                    chunk_count = ?
                WHERE id = ?
                """,
                (
                    processing_status,
                    processed_at.isoformat() if processed_at else None,
                    page_count,
                    chunk_count,
                    file_id,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def get(self, file_id: str) -> PdfMetadata | None:
        """Return the metadata for ``file_id``, or ``None`` if not found."""

        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT id, filename, original_name, size, upload_time, status,
                       user_id, processing_status, processed_at, page_count, chunk_count
                FROM pdf_documents
                WHERE id = ?
                """,
                (file_id,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            return None
        return _row_to_metadata(row)


def _row_to_metadata(row: sqlite3.Row) -> PdfMetadata:
    """Map a database row to a :class:`PdfMetadata` instance."""

    processed_at = row["processed_at"]
    return PdfMetadata(
        id=row["id"],
        filename=row["filename"],
        original_name=row["original_name"],
        size=row["size"],
        upload_time=datetime.fromisoformat(row["upload_time"]),
        status=row["status"],
        user_id=row["user_id"],
        processing_status=row["processing_status"],
        processed_at=datetime.fromisoformat(processed_at) if processed_at else None,
        page_count=row["page_count"],
        chunk_count=row["chunk_count"],
    )
