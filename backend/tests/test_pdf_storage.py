"""Unit tests for the PDF storage service."""

import io

import pytest
from starlette.datastructures import Headers, UploadFile

from app.core.config import settings
from app.services.pdf_storage import PDFStorageService, PDFValidationError


def _make_upload(
    data: bytes,
    filename: str = "doc.pdf",
    content_type: str = "application/pdf",
) -> UploadFile:
    """Build an in-memory UploadFile for testing."""

    headers = Headers({"content-type": content_type})
    return UploadFile(file=io.BytesIO(data), filename=filename, headers=headers)


@pytest.fixture()
def service(tmp_path, monkeypatch) -> PDFStorageService:
    """Provide a storage service writing into a temporary directory."""

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return PDFStorageService()


def test_save_valid_pdf_writes_file(service: PDFStorageService, tmp_path) -> None:
    """A valid PDF should be stored and metadata returned."""

    file_id, stored_name, size = service.save(_make_upload(b"%PDF-1.4 data"))

    assert stored_name == f"{file_id}.pdf"
    assert size == len(b"%PDF-1.4 data")
    assert (tmp_path / stored_name).exists()


def test_save_rejects_non_pdf_content_type(service: PDFStorageService) -> None:
    """A non-PDF content type should be rejected."""

    upload = _make_upload(b"hello", filename="notes.txt", content_type="text/plain")

    with pytest.raises(PDFValidationError):
        service.save(upload)


def test_save_rejects_empty_file(service: PDFStorageService) -> None:
    """An empty file should be rejected."""

    with pytest.raises(PDFValidationError):
        service.save(_make_upload(b""))


def test_save_rejects_oversized_file(service: PDFStorageService, monkeypatch) -> None:
    """A file above the configured size limit should be rejected."""

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    service_with_limit = PDFStorageService()

    with pytest.raises(PDFValidationError):
        service_with_limit.save(_make_upload(b"%PDF-1.4 data"))


def test_save_rejects_corrupted_pdf(service: PDFStorageService) -> None:
    """A file lacking the PDF signature should be rejected as corrupted."""

    corrupted = _make_upload(b"not a real pdf payload")

    with pytest.raises(PDFValidationError):
        service.save(corrupted)
