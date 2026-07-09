"""Application service orchestrating PDF upload and metadata persistence."""

from datetime import datetime, timezone

from fastapi import UploadFile

from app.models.pdf import PdfMetadata
from app.repositories.pdf_repository import PdfMetadataRepository
from app.services.pdf_storage import PDFStorageService

_STATUS_UPLOADED = "uploaded"
_PROCESSING_PENDING = "pending"


class PdfService:
    """Coordinates validated file storage and metadata persistence.

    This is the single home for PDF upload business logic: it stores the
    file via the storage service and records its metadata via the
    repository, returning the resulting domain record.
    """

    def __init__(
        self,
        storage: PDFStorageService,
        repository: PdfMetadataRepository,
    ) -> None:
        self._storage = storage
        self._repository = repository

    def upload(self, file: UploadFile, user_id: str | None = None) -> PdfMetadata:
        """Validate, store, and record an uploaded PDF.

        Args:
            file: The incoming file from the multipart request.
            user_id: Owning user identifier, or ``None`` until auth exists.

        Returns:
            The persisted :class:`PdfMetadata` record.

        Raises:
            PDFValidationError: If the file is not a valid, in-limit PDF.
        """

        file_id, stored_filename, size_bytes = self._storage.save(file)

        record = PdfMetadata(
            id=file_id,
            filename=stored_filename,
            original_name=file.filename or stored_filename,
            size=size_bytes,
            upload_time=datetime.now(timezone.utc),
            status=_STATUS_UPLOADED,
            user_id=user_id,
            processing_status=_PROCESSING_PENDING,
        )
        self._repository.create(record)
        return record
