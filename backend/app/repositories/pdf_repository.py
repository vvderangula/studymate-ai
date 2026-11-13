"""Repository for PDF document metadata."""

from __future__ import annotations

from datetime import datetime

from pymongo import DESCENDING

from app.core.database import Collections
from app.models.pdf import PdfMetadata
from app.repositories.base import MongoRepository, as_utc


class PdfMetadataRepository(MongoRepository):
    """The only component that reads or writes ``pdf_documents``."""

    collection_name = Collections.PDFS

    def create(self, record: PdfMetadata) -> None:
        """Insert a new PDF record."""

        self.collection.insert_one(
            {
                "_id": record.id,
                "filename": record.filename,
                "original_name": record.original_name,
                "size": record.size,
                "upload_time": record.upload_time,
                "status": record.status,
                "user_id": record.user_id,
                "processing_status": record.processing_status,
                "processed_at": record.processed_at,
                "page_count": record.page_count,
                "chunk_count": record.chunk_count,
            }
        )

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

        self.collection.update_one(
            {"_id": file_id},
            {
                "$set": {
                    "processing_status": processing_status,
                    "processed_at": processed_at,
                    "page_count": page_count,
                    "chunk_count": chunk_count,
                }
            },
        )

    def get(self, file_id: str) -> PdfMetadata | None:
        """Return the metadata for ``file_id``, or ``None``."""

        return _to_metadata(self.collection.find_one({"_id": file_id}))

    def list_processed(self) -> list[PdfMetadata]:
        """All completed PDFs, newest first."""

        cursor = self.collection.find({"processing_status": "completed"}).sort(
            "processed_at", DESCENDING
        )
        return [_to_metadata(doc) for doc in cursor]

    def list_by_user(self, user_id: str) -> list[PdfMetadata]:
        """Completed PDFs owned by ``user_id``, newest first."""

        cursor = self.collection.find(
            {"processing_status": "completed", "user_id": user_id}
        ).sort("processed_at", DESCENDING)
        return [_to_metadata(doc) for doc in cursor]

    def list_all_by_user(self, user_id: str) -> list[PdfMetadata]:
        """Every PDF the user uploaded (any status), newest upload first."""

        cursor = self.collection.find({"user_id": user_id}).sort("upload_time", DESCENDING)
        return [_to_metadata(doc) for doc in cursor]

    def delete(self, file_id: str) -> None:
        """Remove a PDF record."""

        self.collection.delete_one({"_id": file_id})


def _to_metadata(doc: dict | None) -> PdfMetadata | None:
    if doc is None:
        return None
    return PdfMetadata(
        id=doc["_id"],
        filename=doc["filename"],
        original_name=doc["original_name"],
        size=doc["size"],
        upload_time=as_utc(doc["upload_time"]),
        status=doc["status"],
        user_id=doc.get("user_id"),
        processing_status=doc.get("processing_status", "pending"),
        processed_at=as_utc(doc.get("processed_at")),
        page_count=doc.get("page_count"),
        chunk_count=doc.get("chunk_count"),
    )
