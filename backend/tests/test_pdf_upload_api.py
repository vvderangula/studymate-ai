"""API tests for the PDF upload endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import init_db
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Redirect uploads and the database to a temporary location per test."""

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    init_db()
    yield


def _upload(data: bytes, filename: str = "doc.pdf", content_type: str = "application/pdf"):
    """Post a file to the upload endpoint."""

    return client.post(
        "/pdf/upload",
        files={"file": (filename, data, content_type)},
    )


def test_upload_valid_pdf_returns_metadata() -> None:
    """A valid PDF upload should return 201 with full metadata."""

    response = _upload(b"%PDF-1.4 valid content")

    assert response.status_code == 201
    body = response.json()
    assert body["original_name"] == "doc.pdf"
    assert body["filename"] == f"{body['id']}.pdf"
    assert body["size"] == len(b"%PDF-1.4 valid content")
    assert body["status"] == "uploaded"
    assert body["user_id"] is None
    assert "upload_time" in body


def test_upload_rejects_invalid_extension() -> None:
    """A non-.pdf extension should be rejected with 400."""

    response = _upload(b"%PDF-1.4 data", filename="notes.txt")

    assert response.status_code == 400


def test_upload_rejects_invalid_mime() -> None:
    """A non-PDF content type should be rejected with 400."""

    response = _upload(b"%PDF-1.4 data", content_type="text/plain")

    assert response.status_code == 400


def test_upload_rejects_corrupted_pdf() -> None:
    """A file missing the PDF signature should be rejected with 400."""

    response = _upload(b"this is not a pdf")

    assert response.status_code == 400


def test_upload_rejects_oversized_file(monkeypatch) -> None:
    """A file above the configured size limit should be rejected with 400."""

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)

    response = _upload(b"%PDF-1.4 data")

    assert response.status_code == 400
