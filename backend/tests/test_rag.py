"""Unit tests for the prompt builder and RAG orchestration."""

import pytest

from app.services.rag.prompt_builder import PromptBuilder
from app.services.rag.rag_service import (
    PdfNotFoundError,
    PdfNotProcessedError,
    RAGService,
)
from app.services.vector_store.retrieval import RetrievedChunk


class _FakeRetriever:
    """Returns a fixed set of context chunks."""

    def __init__(self, chunks: list[str], cited: list[RetrievedChunk] | None = None) -> None:
        self._chunks = chunks
        self._cited = cited or []
        self.calls: list[tuple[str, str]] = []

    def retrieve(self, file_id: str, query: str, top_k=None) -> list[str]:
        self.calls.append((file_id, query))
        return self._chunks

    def retrieve_with_citations(
        self, file_id: str, query: str, top_k=None
    ) -> list[RetrievedChunk]:
        self.calls.append((file_id, query))
        return self._cited


class _FakeLLM:
    """Echoes the prompts it receives so we can assert on them."""

    def __init__(self) -> None:
        self.system_prompt = ""
        self.user_prompt = ""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return "generated answer"


class _FakeIndexer:
    """Fake embedding indexer reporting a fixed number of vectors."""

    def __init__(self, indexed: int) -> None:
        self._indexed = indexed
        self.calls: list[str] = []

    def ensure_indexed(self, file_id: str) -> int:
        self.calls.append(file_id)
        return self._indexed


class _FakeRecord:
    """Minimal PDF record exposing the citation source name."""

    original_name = "notes.pdf"


class _FakeRepository:
    """Returns a fixed record (or ``None``) for any file id."""

    def __init__(self, record) -> None:
        self._record = record

    def get(self, file_id: str):
        return self._record



def test_user_prompt_includes_context_and_question() -> None:
    """The user prompt should embed numbered context and the question."""

    builder = PromptBuilder()

    prompt = builder.user_prompt(["chunk one", "chunk two"], "What is X?")

    assert "[1] chunk one" in prompt
    assert "[2] chunk two" in prompt
    assert "What is X?" in prompt


def test_user_prompt_handles_no_context() -> None:
    """With no chunks, the prompt should note the absence of context."""

    builder = PromptBuilder()

    prompt = builder.user_prompt([], "What is X?")

    assert "no relevant context" in prompt


def test_rag_service_returns_answer_and_context() -> None:
    """RAGService should retrieve, prompt, and return the answer + context."""

    retriever = _FakeRetriever(["alpha", "beta"])
    llm = _FakeLLM()
    service = RAGService(retriever, PromptBuilder(), llm)

    answer, context = service.answer("file1", "Why?")

    assert answer == "generated answer"
    assert context == ["alpha", "beta"]
    assert retriever.calls == [("file1", "Why?")]
    assert "alpha" in llm.user_prompt


def test_user_prompt_cited_includes_page_labels() -> None:
    """The cited prompt should label each context chunk with its page."""

    builder = PromptBuilder()
    chunks = [
        RetrievedChunk(text="alpha", chunk_id="f-0", chunk_index=0, page=2),
        RetrievedChunk(text="beta", chunk_id="f-1", chunk_index=1, page=5),
    ]

    prompt = builder.user_prompt_cited(chunks, "What is X?")

    assert "(page 2) alpha" in prompt
    assert "(page 5) beta" in prompt
    assert "What is X?" in prompt


def test_answer_with_citations_returns_answer_and_citations() -> None:
    """The cited pipeline should embed, retrieve, and build citations."""

    cited = [
        RetrievedChunk(text="alpha", chunk_id="file1-0", chunk_index=0, page=3),
        RetrievedChunk(text="beta", chunk_id="file1-1", chunk_index=1, page=7),
    ]
    retriever = _FakeRetriever([], cited=cited)
    indexer = _FakeIndexer(indexed=2)
    repository = _FakeRepository(_FakeRecord())
    service = RAGService(
        retriever,
        PromptBuilder(),
        _FakeLLM(),
        indexer=indexer,
        repository=repository,
    )

    result = service.answer_with_citations("file1", "Why?")

    assert result.answer == "generated answer"
    assert indexer.calls == ["file1"]
    assert result.metadata["chunks_retrieved"] == 2
    assert result.metadata["file_id"] == "file1"
    pages = [citation.page for citation in result.citations]
    chunk_ids = [citation.chunk_id for citation in result.citations]
    assert pages == [3, 7]
    assert chunk_ids == ["file1-0", "file1-1"]
    assert result.citations[0].source_reference == "notes.pdf, page 3"


def test_answer_with_citations_unknown_pdf_raises() -> None:
    """A missing PDF record should raise PdfNotFoundError."""

    service = RAGService(
        _FakeRetriever([]),
        PromptBuilder(),
        _FakeLLM(),
        indexer=_FakeIndexer(indexed=1),
        repository=_FakeRepository(None),
    )

    with pytest.raises(PdfNotFoundError):
        service.answer_with_citations("missing", "Why?")


def test_answer_with_citations_unprocessed_pdf_raises() -> None:
    """A PDF with no embedded chunks should raise PdfNotProcessedError."""

    service = RAGService(
        _FakeRetriever([]),
        PromptBuilder(),
        _FakeLLM(),
        indexer=_FakeIndexer(indexed=0),
        repository=_FakeRepository(_FakeRecord()),
    )

    with pytest.raises(PdfNotProcessedError):
        service.answer_with_citations("file1", "Why?")

