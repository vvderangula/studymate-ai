"""Unit tests for the PDF embedding service."""

from pathlib import Path

from app.services.pdf_embedding_service import PdfEmbeddingService


class _FakeStorage:
    """Returns a fixed path for a stored PDF."""

    def __init__(self, path: Path | None) -> None:
        self._path = path

    def path_for(self, file_id: str) -> Path | None:
        return self._path


class _FakeExtractor:
    """Returns predetermined per-page text."""

    def __init__(self, pages: list[str]) -> None:
        self._pages = pages

    def extract_pages(self, path) -> list[str]:  # noqa: ANN001 - test double
        return self._pages


class _FakeChunkStorage:
    """Returns predetermined stored chunks."""

    def __init__(self, chunks: list[str] | None) -> None:
        self._chunks = chunks

    def load(self, file_id: str) -> list[str] | None:
        return self._chunks


class _FakeEmbeddings:
    """Deterministic fake embedding service that records calls."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(len(text))] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))]


class _FakeChroma:
    """Records add_documents calls and reports a configurable count."""

    def __init__(self, count: int = 0) -> None:
        self._count = count
        self.added: dict | None = None

    def count(self, file_id: str) -> int:
        return self._count

    def add_documents(self, file_id, *, ids, embeddings, documents, metadatas) -> None:
        self.added = {
            "file_id": file_id,
            "ids": ids,
            "embeddings": embeddings,
            "documents": documents,
            "metadatas": metadatas,
        }


def _build(storage, extractor, chunk_storage, embeddings, chroma) -> PdfEmbeddingService:
    return PdfEmbeddingService(storage, extractor, chunk_storage, embeddings, chroma)


def test_ensure_indexed_embeds_chunks_with_page_metadata() -> None:
    """Chunks should be embedded and stored with page and chunk-id metadata."""

    embeddings = _FakeEmbeddings()
    chroma = _FakeChroma(count=0)
    service = _build(
        _FakeStorage(Path("doc.pdf")),
        _FakeExtractor(["alpha text", "beta text"]),
        _FakeChunkStorage(["alpha text", "beta text"]),
        embeddings,
        chroma,
    )

    count = service.ensure_indexed("file1")

    assert count == 2
    assert embeddings.calls == [["alpha text", "beta text"]]
    assert chroma.added is not None
    assert chroma.added["ids"] == ["file1-0", "file1-1"]
    pages = [meta["page"] for meta in chroma.added["metadatas"]]
    assert pages == [1, 2]
    assert chroma.added["metadatas"][0]["chunk_id"] == "file1-0"


def test_ensure_indexed_skips_when_already_embedded() -> None:
    """Already embedded documents should be skipped without re-embedding."""

    embeddings = _FakeEmbeddings()
    chroma = _FakeChroma(count=5)
    service = _build(
        _FakeStorage(Path("doc.pdf")),
        _FakeExtractor(["alpha"]),
        _FakeChunkStorage(["alpha"]),
        embeddings,
        chroma,
    )

    count = service.ensure_indexed("file1")

    assert count == 5
    assert embeddings.calls == []
    assert chroma.added is None


def test_ensure_indexed_returns_zero_without_chunks() -> None:
    """A PDF with no stored chunks should not be embedded."""

    embeddings = _FakeEmbeddings()
    chroma = _FakeChroma(count=0)
    service = _build(
        _FakeStorage(Path("doc.pdf")),
        _FakeExtractor([]),
        _FakeChunkStorage(None),
        embeddings,
        chroma,
    )

    assert service.ensure_indexed("file1") == 0
    assert embeddings.calls == []
    assert chroma.added is None


def test_page_numbers_fall_back_when_source_missing() -> None:
    """When the source file is missing, all chunks default to page 1."""

    embeddings = _FakeEmbeddings()
    chroma = _FakeChroma(count=0)
    service = _build(
        _FakeStorage(None),
        _FakeExtractor(["ignored"]),
        _FakeChunkStorage(["alpha", "beta"]),
        embeddings,
        chroma,
    )

    service.ensure_indexed("file1")

    pages = [meta["page"] for meta in chroma.added["metadatas"]]
    assert pages == [1, 1]
