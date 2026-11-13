"""Unit tests for the PDF upload service."""

import io

import pytest
from starlette.datastructures import Headers, UploadFile

from app.core.config import settings
from app.repositories.pdf_repository import PdfMetadataRepository
from app.services.pdf_service import PdfService
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
def service(tmp_path, monkeypatch) -> PdfService:
    """Provide a PdfService backed by isolated file and database storage."""

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    return PdfService(PDFStorageService(), PdfMetadataRepository())


def test_upload_persists_metadata(service: PdfService) -> None:
    """A valid upload should store the file and persist its metadata."""

    record = service.upload(_make_upload(b"%PDF-1.4 sample"), user_id=None)

    assert record.original_name == "doc.pdf"
    assert record.filename == f"{record.id}.pdf"
    assert record.size == len(b"%PDF-1.4 sample")
    assert record.status == "uploaded"
    assert record.user_id is None

    stored = PdfMetadataRepository().get(record.id)
    assert stored is not None
    assert stored.id == record.id
    assert stored.original_name == "doc.pdf"


def test_upload_rejects_invalid_file(service: PdfService) -> None:
    """An invalid file should raise and persist no metadata."""

    with pytest.raises(PDFValidationError):
        service.upload(_make_upload(b"not a pdf"))

    assert PdfMetadataRepository().collection.count_documents({}) == 0
