"""API tests for the PDF chat endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes.pdf import get_rag_service
from app.main import app
from app.services.rag.rag_service import (
    Citation,
    PdfNotFoundError,
    PdfNotProcessedError,
    RagResult,
)

client = TestClient(app)


class _StubRAGService:
    """Configurable stand-in for RAGService used via dependency override."""

    def __init__(self, result: RagResult | None = None, error: Exception | None = None):
        self._result = result
        self._error = error
        self.calls: list[tuple[str, str]] = []

    def answer_with_citations(self, file_id: str, question: str) -> RagResult:
        self.calls.append((file_id, question))
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _override(service: _StubRAGService) -> None:
    app.dependency_overrides[get_rag_service] = lambda: service


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_chat_returns_answer_with_citations() -> None:
    """A successful chat should return the answer, citations, and metadata."""

    result = RagResult(
        answer="The answer.",
        citations=[
            Citation(page=3, chunk_id="file1-0", source_reference="notes.pdf, page 3"),
            Citation(page=5, chunk_id="file1-1", source_reference="notes.pdf, page 5"),
        ],
        metadata={"file_id": "file1", "chunks_retrieved": 2, "top_k": 4},
    )
    _override(_StubRAGService(result=result))

    response = client.post("/pdf/file1/chat", json={"question": "What is X?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The answer."
    assert body["metadata"]["chunks_retrieved"] == 2
    assert len(body["citations"]) == 2
    assert body["citations"][0]["page"] == 3
    assert body["citations"][0]["chunk_id"] == "file1-0"
    assert body["citations"][0]["source_reference"] == "notes.pdf, page 3"


def test_chat_empty_question_returns_400() -> None:
    """A blank question should be rejected before reaching the service."""

    stub = _StubRAGService(result=RagResult("", [], {}))
    _override(stub)

    response = client.post("/pdf/file1/chat", json={"question": "   "})

    assert response.status_code == 400
    assert stub.calls == []


def test_chat_unknown_pdf_returns_404() -> None:
    """An unknown PDF should yield a 404 response."""

    _override(_StubRAGService(error=PdfNotFoundError("File not found.")))

    response = client.post("/pdf/missing/chat", json={"question": "What is X?"})

    assert response.status_code == 404


def test_chat_unprocessed_pdf_returns_422() -> None:
    """A PDF that has not been processed should yield a 422 response."""

    _override(_StubRAGService(error=PdfNotProcessedError("Not processed.")))

    response = client.post("/pdf/file1/chat", json={"question": "What is X?"})

    assert response.status_code == 422
