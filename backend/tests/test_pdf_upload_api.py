"""API tests for the PDF upload endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Redirect uploads and the database to a temporary location per test."""

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    yield


def _upload(data: bytes, filename: str = "doc.pdf", content_type: str = "application/pdf", headers: dict | None = None):
    """Post a file to the upload endpoint."""

    return client.post(
        "/pdf/upload",
        files={"file": (filename, data, content_type)},
        headers=headers or {},
    )


def test_upload_valid_pdf_returns_metadata(auth_headers) -> None:
    """A valid PDF upload should return 201 with full metadata."""

    response = _upload(b"%PDF-1.4 valid content", headers=auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["original_name"] == "doc.pdf"
    assert body["filename"] == f"{body['id']}.pdf"
    assert body["size"] == len(b"%PDF-1.4 valid content")
    assert body["status"] == "uploaded"
    assert "upload_time" in body


def test_upload_rejects_invalid_extension(auth_headers) -> None:
    """A non-.pdf extension should be rejected with 400."""

    response = _upload(b"%PDF-1.4 data", filename="notes.txt", headers=auth_headers)

    assert response.status_code == 400


def test_upload_rejects_invalid_mime(auth_headers) -> None:
    """A non-PDF content type should be rejected with 400."""

    response = _upload(b"%PDF-1.4 data", content_type="text/plain", headers=auth_headers)

    assert response.status_code == 400


def test_upload_rejects_corrupted_pdf(auth_headers) -> None:
    """A file missing the PDF signature should be rejected with 400."""

    response = _upload(b"this is not a pdf", headers=auth_headers)

    assert response.status_code == 400


def test_upload_rejects_oversized_file(monkeypatch, auth_headers) -> None:
    """A file above the configured size limit should be rejected with 400."""

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)

    response = _upload(b"%PDF-1.4 data", headers=auth_headers)

    assert response.status_code == 400
