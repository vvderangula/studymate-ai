"""Unit and API tests for the PDF processing pipeline."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import init_db
from app.main import app
from app.models.pdf import PdfMetadata
from app.repositories.pdf_repository import PdfMetadataRepository
from app.services.chunk_storage import ChunkStorageService
from app.services.pdf_extractor import PDFExtractionError, PDFExtractor
from app.services.pdf_processing_service import (
    ProcessingConfig,
    ProcessingError,
    ProcessingNotFoundError,
    ProcessingService,
)
from app.services.pdf_storage import PDFStorageService
from app.services.text_chunker import TextChunker


class _StubExtractor:
    """Extractor stub returning predetermined pages or raising an error."""

    def __init__(self, pages: list[str] | None = None, error: bool = False) -> None:
        self._pages = pages or []
        self._error = error

    def extract_pages(self, path) -> list[str]:  # noqa: ANN001 - test double
        if self._error:
            raise PDFExtractionError("Failed to read the PDF file.")
        return self._pages


def _write_pdf(directory, file_id: str) -> None:
    """Create a placeholder stored PDF file for a given id."""

    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{file_id}.pdf").write_bytes(b"%PDF-1.4 stored bytes")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolate uploads, chunk storage, and the database per test."""

    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    monkeypatch.setattr(settings, "chunks_dir", str(tmp_path / "chunks"))
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "chunk_size", 50)
    monkeypatch.setattr(settings, "chunk_overlap", 10)
    init_db()
    return {"upload_dir": upload_dir}


def _seed_record(file_id: str = "doc1") -> PdfMetadata:
    """Insert a pending PDF record and return it."""

    record = PdfMetadata(
        id=file_id,
        filename=f"{file_id}.pdf",
        original_name="doc.pdf",
        size=20,
        upload_time=datetime.now(timezone.utc),
        status="uploaded",
        processing_status="pending",
    )
    PdfMetadataRepository().create(record)
    return record


def _build_service(pages=None, error=False) -> ProcessingService:
    """Construct a ProcessingService with a stubbed extractor."""

    return ProcessingService(
        ProcessingConfig(
            storage=PDFStorageService(),
            extractor=_StubExtractor(pages=pages, error=error),
            chunker=TextChunker(),
            chunk_storage=ChunkStorageService(),
            repository=PdfMetadataRepository(),
        )
    )


def test_process_valid_pdf_completes(env) -> None:
    """A PDF with extractable text should complete with counts and chunks."""

    _seed_record("doc1")
    _write_pdf(env["upload_dir"], "doc1")
    service = _build_service(pages=["Page one text.", "Page two text."])

    result = service.process("doc1")

    assert result.processing_status == "completed"
    assert result.processed_at is not None
    assert result.page_count == 2
    assert result.chunk_count is not None and result.chunk_count >= 1

    stored_chunks = ChunkStorageService().load("doc1")
    assert stored_chunks is not None
    assert len(stored_chunks) == result.chunk_count


def test_process_scanned_pdf_without_text_fails(env) -> None:
    """A scanned PDF (no extractable text) should be marked failed."""

    _seed_record("doc2")
    _write_pdf(env["upload_dir"], "doc2")
    service = _build_service(pages=["", "   ", "\n\t"])

    with pytest.raises(ProcessingError):
        service.process("doc2")

    record = PdfMetadataRepository().get("doc2")
    assert record is not None
    assert record.processing_status == "failed"
    assert record.processed_at is not None


def test_process_corrupted_pdf_fails(env) -> None:
    """A corrupted PDF that cannot be read should be marked failed."""

    _seed_record("doc3")
    _write_pdf(env["upload_dir"], "doc3")
    service = _build_service(error=True)

    with pytest.raises(ProcessingError):
        service.process("doc3")

    record = PdfMetadataRepository().get("doc3")
    assert record is not None
    assert record.processing_status == "failed"


def test_process_large_pdf_generates_many_chunks(env) -> None:
    """A large PDF should process into many chunks and complete."""

    _seed_record("doc4")
    _write_pdf(env["upload_dir"], "doc4")
    pages = [f"Section {i} " + ("content " * 40) for i in range(30)]
    service = _build_service(pages=pages)

    result = service.process("doc4")

    assert result.processing_status == "completed"
    assert result.page_count == 30
    assert result.chunk_count is not None and result.chunk_count > 10


def test_process_normalizes_whitespace_in_chunks(env) -> None:
    """Chunk generation should collapse excess whitespace from pages."""

    _seed_record("doc5")
    _write_pdf(env["upload_dir"], "doc5")
    service = _build_service(pages=["  messy   \n\n  text   here \t end  "])

    service.process("doc5")

    chunks = ChunkStorageService().load("doc5")
    assert chunks is not None
    assert chunks[0] == "messy text here end"


def test_process_updates_status_from_pending_to_completed(env) -> None:
    """Processing should transition the stored status to completed."""

    _seed_record("doc6")
    _write_pdf(env["upload_dir"], "doc6")

    before = PdfMetadataRepository().get("doc6")
    assert before is not None and before.processing_status == "pending"

    _build_service(pages=["Some readable text."]).process("doc6")

    after = PdfMetadataRepository().get("doc6")
    assert after is not None
    assert after.processing_status == "completed"


def test_process_unknown_file_raises_not_found(env) -> None:
    """Processing an unknown id should raise a not-found error."""

    service = _build_service(pages=["text"])

    with pytest.raises(ProcessingNotFoundError):
        service.process("missing")


def test_extractor_rejects_corrupted_bytes(tmp_path) -> None:
    """The real extractor should raise on unreadable PDF bytes."""

    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a real pdf")

    with pytest.raises(PDFExtractionError):
        PDFExtractor().extract_pages(bad)


# --- API-level tests using a dependency override -------------------------------

client = TestClient(app)


@pytest.fixture()
def api_env(tmp_path, monkeypatch):
    """Isolate storage/database and override the processing dependency."""

    from app.api.routes.pdf import get_processing_service

    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    monkeypatch.setattr(settings, "chunks_dir", str(tmp_path / "chunks"))
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    init_db()

    def _override(pages=None, error=False):
        app.dependency_overrides[get_processing_service] = lambda: _build_service(
            pages=pages, error=error
        )

    yield {"upload_dir": upload_dir, "override": _override}
    app.dependency_overrides.clear()


def test_api_process_valid_returns_metadata(api_env, auth_headers) -> None:
    """A successful process call should return 200 with processing metadata."""

    _seed_record("api1")
    _write_pdf(api_env["upload_dir"], "api1")
    api_env["override"](pages=["Readable page text."])

    response = client.post("/pdf/api1/process", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "api1"
    assert body["processing_status"] == "completed"
    assert body["page_count"] == 1
    assert body["chunk_count"] >= 1


def test_api_process_corrupted_returns_422(api_env, auth_headers) -> None:
    """A corrupted PDF should yield a 422 response."""

    _seed_record("api2")
    _write_pdf(api_env["upload_dir"], "api2")
    api_env["override"](error=True)

    response = client.post("/pdf/api2/process", headers=auth_headers)

    assert response.status_code == 422


def test_api_process_unknown_returns_404(api_env, auth_headers) -> None:
    """An unknown file id should yield a 404 response."""

    api_env["override"](pages=["text"])

    response = client.post("/pdf/missing/process", headers=auth_headers)

    assert response.status_code == 404
