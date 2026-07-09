"""Storage service for validating and persisting uploaded PDF files."""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

_PDF_CONTENT_TYPE = "application/pdf"
_PDF_SUFFIX = ".pdf"
_PDF_MAGIC = b"%PDF-"


class PDFValidationError(Exception):
    """Raised when an uploaded file fails validation."""


class PDFStorageService:
    """Validates uploaded PDFs and stores them on the local filesystem.

    Single responsibility: turn an ``UploadFile`` into a safely-named file on
    disk, enforcing type and size constraints at the system boundary.
    """

    def __init__(self) -> None:
        self._upload_dir = Path(settings.upload_dir)
        self._max_bytes = settings.max_upload_size_mb * 1024 * 1024
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file: UploadFile) -> tuple[str, str, int]:
        """Validate and persist an uploaded PDF.

        Args:
            file: The incoming file from the multipart request.

        Returns:
            A tuple of ``(file_id, stored_filename, size_bytes)``.

        Raises:
            PDFValidationError: If the file is not a valid, in-limit PDF.
        """

        self._validate_type(file)

        data = file.file.read()
        self._validate_size(len(data))
        self._validate_signature(data)

        file_id = uuid.uuid4().hex
        stored_filename = f"{file_id}{_PDF_SUFFIX}"
        destination = self._upload_dir / stored_filename
        destination.write_bytes(data)

        return file_id, stored_filename, len(data)

    def path_for(self, file_id: str) -> Path | None:
        """Return the stored file path for a ``file_id``, or ``None`` if absent."""

        candidate = self._upload_dir / f"{file_id}{_PDF_SUFFIX}"
        return candidate if candidate.is_file() else None

    def _validate_type(self, file: UploadFile) -> None:
        """Ensure the file declares a PDF content type and extension."""

        filename = file.filename or ""
        if file.content_type != _PDF_CONTENT_TYPE:
            raise PDFValidationError("Only PDF files are allowed.")
        if not filename.lower().endswith(_PDF_SUFFIX):
            raise PDFValidationError("File must have a .pdf extension.")

    def _validate_size(self, size_bytes: int) -> None:
        """Ensure the file is non-empty and within the size limit."""

        if size_bytes == 0:
            raise PDFValidationError("Uploaded file is empty.")
        if size_bytes > self._max_bytes:
            limit_mb = settings.max_upload_size_mb
            raise PDFValidationError(f"File exceeds the {limit_mb} MB limit.")

    def _validate_signature(self, data: bytes) -> None:
        """Ensure the file content begins with the PDF magic bytes.

        Guards against corrupted files or non-PDF payloads disguised with a
        PDF content type or extension.
        """

        if not data.startswith(_PDF_MAGIC):
            raise PDFValidationError("File is not a valid PDF (missing PDF signature).")
