"""Tests for the Learn from YouTube module."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes.youtube import get_rag_service, get_youtube_processor
from app.main import app
from app.models.youtube import YoutubeMetadata
from app.services.rag.rag_service import (
    Citation,
    PdfNotFoundError,
    PdfNotProcessedError,
    RagResult,
)
from app.services.text_chunker import TextChunker
from app.services.youtube.transcript_service import (
    InvalidYoutubeUrlError,
    TranscriptSegment,
    TranscriptUnavailableError,
    VideoTranscript,
    extract_video_id,
)
from app.services.youtube.youtube_processing_service import YoutubeProcessingService

client = TestClient(app)


# --- URL validation -------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?list=abc&v=dQw4w9WgXcQ",
    ],
)
def test_extract_video_id_accepts_known_forms(url: str) -> None:
    """The 11-character id should be extracted from common URL shapes."""

    assert extract_video_id(url) == "dQw4w9WgXcQ"


@pytest.mark.parametrize("url", ["", "not a url", "https://example.com/video"])
def test_extract_video_id_rejects_invalid(url: str) -> None:
    """Non-YouTube or empty URLs should raise a validation error."""

    with pytest.raises(InvalidYoutubeUrlError):
        extract_video_id(url)


# --- Processing pipeline --------------------------------------------------


class _FakeTranscripts:
    """Returns a fixed transcript, or raises the configured error."""

    def __init__(self, transcript: VideoTranscript | None, error: Exception | None = None):
        self._transcript = transcript
        self._error = error

    def fetch(self, url: str) -> VideoTranscript:
        if self._error is not None:
            raise self._error
        assert self._transcript is not None
        return self._transcript


class _FakeChunkStorage:
    def __init__(self) -> None:
        self.saved: dict[str, list[str]] = {}

    def save(self, file_id: str, chunks: list[str]):
        self.saved[file_id] = chunks
        return None


class _FakeEmbeddings:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))]


class _FakeChroma:
    def __init__(self) -> None:
        self.added: dict = {}

    def add_documents(self, file_id, *, ids, embeddings, documents, metadatas):
        self.added = {
            "file_id": file_id,
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }

    def count(self, file_id: str) -> int:
        return len(self.added.get("ids", [])) if self.added.get("file_id") == file_id else 0


class _FakeRepository:
    def __init__(self) -> None:
        self.record: YoutubeMetadata | None = None

    def upsert(self, record: YoutubeMetadata) -> None:
        self.record = record

    def get(self, video_id: str):
        return self.record


def _sample_transcript() -> VideoTranscript:
    return VideoTranscript(
        video_id="vid12345678",
        title="Sample Lecture",
        thumbnail="https://img/thumb.jpg",
        duration=30,
        segments=[
            TranscriptSegment(text="Hello world this is intro", start=0.0),
            TranscriptSegment(text="now the second topic begins here", start=10.0),
            TranscriptSegment(text="finally the third and last part", start=30.0),
        ],
    )


def _build_service(**overrides) -> tuple[YoutubeProcessingService, dict]:
    parts = {
        "transcripts": _FakeTranscripts(_sample_transcript()),
        "chunker": TextChunker(chunk_size=30, overlap=0),
        "chunk_storage": _FakeChunkStorage(),
        "embeddings": _FakeEmbeddings(),
        "chroma": _FakeChroma(),
        "repository": _FakeRepository(),
    }
    parts.update(overrides)
    service = YoutubeProcessingService(
        parts["transcripts"],
        parts["chunker"],
        parts["chunk_storage"],
        parts["embeddings"],
        parts["chroma"],
        parts["repository"],
    )
    return service, parts


def test_process_chunks_embeds_and_maps_timestamps() -> None:
    """Processing should chunk, embed, and attach timestamp citations."""

    service, parts = _build_service()

    record = service.process("https://youtu.be/vid12345678")

    assert record.video_id == "vid12345678"
    assert record.processing_status == "completed"
    assert record.chunk_count == 3
    assert parts["chunk_storage"].saved["vid12345678"]

    metadatas = parts["chroma"].added["metadatas"]
    assert [meta["page"] for meta in metadatas] == [0, 10, 30]
    assert [meta["source_reference"] for meta in metadatas] == ["0:00", "0:10", "0:30"]


def test_ensure_indexed_reports_vector_count() -> None:
    """After processing, ensure_indexed should report the vector count."""

    service, _ = _build_service()
    service.process("https://youtu.be/vid12345678")

    assert service.ensure_indexed("vid12345678") == 3


def test_process_without_transcript_raises() -> None:
    """A video without a transcript should surface a clear error."""

    service, _ = _build_service(
        transcripts=_FakeTranscripts(None, TranscriptUnavailableError("no transcript"))
    )

    with pytest.raises(TranscriptUnavailableError):
        service.process("https://youtu.be/vid12345678")


# --- API routes -----------------------------------------------------------


class _StubProcessor:
    def __init__(self, record: YoutubeMetadata | None = None, error: Exception | None = None):
        self._record = record
        self._error = error

    def process(self, url: str, user_id: str | None = None) -> YoutubeMetadata:
        if self._error is not None:
            raise self._error
        assert self._record is not None
        return self._record


class _StubRAGService:
    def __init__(self, result: RagResult | None = None, error: Exception | None = None):
        self._result = result
        self._error = error
        self.calls: list[tuple[str, str]] = []

    def answer_with_citations(self, video_id: str, question: str) -> RagResult:
        self.calls.append((video_id, question))
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_process_route_returns_metadata(auth_headers) -> None:
    """A successful process call returns the stored video metadata."""

    record = YoutubeMetadata(
        video_id="vid12345678",
        url="https://youtu.be/vid12345678",
        title="Sample Lecture",
        duration=30,
        thumbnail="https://img/thumb.jpg",
        processing_status="completed",
        chunk_count=3,
    )
    app.dependency_overrides[get_youtube_processor] = lambda: _StubProcessor(record=record)

    response = client.post("/youtube/process", json={"url": "https://youtu.be/vid12345678"}, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["video_id"] == "vid12345678"
    assert body["title"] == "Sample Lecture"
    assert body["chunk_count"] == 3


def test_process_route_invalid_url_returns_400(auth_headers) -> None:
    """An invalid URL should be rejected with a 400."""

    app.dependency_overrides[get_youtube_processor] = lambda: _StubProcessor(
        error=InvalidYoutubeUrlError("bad url")
    )

    response = client.post("/youtube/process", json={"url": "nope"}, headers=auth_headers)

    assert response.status_code == 400


def test_process_route_missing_transcript_returns_422(auth_headers) -> None:
    """A missing transcript should be reported as 422."""

    app.dependency_overrides[get_youtube_processor] = lambda: _StubProcessor(
        error=TranscriptUnavailableError("no transcript")
    )

    response = client.post("/youtube/process", json={"url": "https://youtu.be/vid12345678"}, headers=auth_headers)

    assert response.status_code == 422


def test_chat_route_returns_timestamp_citations(auth_headers) -> None:
    """Chat should return the answer with timestamp-based citations."""

    result = RagResult(
        answer="It covers three topics.",
        citations=[
            Citation(page=10, chunk_id="vid-1", source_reference="0:10"),
            Citation(page=30, chunk_id="vid-2", source_reference="0:30"),
        ],
        metadata={"file_id": "vid12345678", "chunks_retrieved": 2, "top_k": 4},
    )
    app.dependency_overrides[get_rag_service] = lambda: _StubRAGService(result=result)

    response = client.post("/youtube/vid12345678/chat", json={"question": "What is it about?"}, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "It covers three topics."
    assert body["citations"][0]["source_reference"] == "0:10"
    assert body["citations"][0]["page"] == 10


def test_chat_route_empty_question_returns_400(auth_headers) -> None:
    """A blank question should be rejected before reaching the service."""

    stub = _StubRAGService(result=RagResult("", [], {}))
    app.dependency_overrides[get_rag_service] = lambda: stub

    response = client.post("/youtube/vid12345678/chat", json={"question": "  "}, headers=auth_headers)

    assert response.status_code == 400
    assert stub.calls == []


def test_chat_route_unknown_video_returns_404(auth_headers) -> None:
    """An unknown video should yield a 404 response."""

    app.dependency_overrides[get_rag_service] = lambda: _StubRAGService(
        error=PdfNotFoundError("missing")
    )

    response = client.post("/youtube/missing/chat", json={"question": "What is it?"}, headers=auth_headers)

    assert response.status_code == 404


def test_chat_route_unprocessed_video_returns_422(auth_headers) -> None:
    """A video that has not been processed should yield a 422 response."""

    app.dependency_overrides[get_rag_service] = lambda: _StubRAGService(
        error=PdfNotProcessedError("not processed")
    )

    response = client.post("/youtube/vid12345678/chat", json={"question": "What is it?"}, headers=auth_headers)

    assert response.status_code == 422
