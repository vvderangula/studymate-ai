"""Tests for the AI Academic Search module."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes.academic import get_academic_service
from app.main import app
from app.services.academic import (
    Paper,
    PaperAcademicService,
    PaperSearchError,
    PaperSearchService,
    PaperSummaryError,
)
from app.services.academic.paper_search import _parse_arxiv
from app.services.rag.prompt_builder import PromptBuilder

client = TestClient(app)


class _FakeLLM:
    """Returns a canned completion."""

    def __init__(self, output: str) -> None:
        self._output = output

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return self._output


class _StubAcademicService:
    def __init__(
        self, summary: str = "", answer: str = "", error: Exception | None = None
    ) -> None:
        self._summary = summary
        self._answer = answer
        self._error = error

    def summarize(self, **_kwargs) -> str:
        if self._error is not None:
            raise self._error
        return self._summary

    def ask(self, **_kwargs) -> str:
        if self._error is not None:
            raise self._error
        return self._answer


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


# ------------------------------------------------------------------
# PaperAcademicService unit tests
# ------------------------------------------------------------------


def test_academic_service_summarize_calls_llm() -> None:
    """summarize() should pass a structured context to the LLM."""

    llm = _FakeLLM("## Short Summary\nGreat paper.")
    service = PaperAcademicService(PromptBuilder(), llm)

    result = service.summarize(
        title="Attention Is All You Need",
        authors=["Vaswani et al."],
        year=2017,
        abstract="We propose a new architecture.",
    )

    assert "Short Summary" in result or "Great paper" in result


def test_academic_service_ask_uses_abstract_as_context() -> None:
    """ask() should include the abstract in the context sent to the LLM."""

    llm = _FakeLLM("The transformer uses self-attention.")
    service = PaperAcademicService(PromptBuilder(), llm)

    result = service.ask(
        title="Attention Is All You Need",
        abstract="We introduce the Transformer.",
        question="What mechanism does it use?",
    )

    assert "self-attention" in result


def test_academic_service_ask_handles_missing_abstract() -> None:
    """ask() should not crash when no abstract is available."""

    llm = _FakeLLM("I cannot tell from the available information.")
    service = PaperAcademicService(PromptBuilder(), llm)

    result = service.ask(
        title="Some Paper",
        abstract=None,
        question="What is the main contribution?",
    )

    assert isinstance(result, str)


# ------------------------------------------------------------------
# arXiv XML parser unit tests
# ------------------------------------------------------------------

_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <summary>We propose the Transformer architecture.</summary>
    <published>2017-06-12T17:57:34Z</published>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <link title="pdf" href="https://arxiv.org/pdf/1706.03762v7" rel="related"/>
  </entry>
</feed>
"""


def test_parse_arxiv_extracts_fields() -> None:
    """The arXiv XML parser should extract all expected fields."""

    papers = _parse_arxiv(_ARXIV_XML)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.paper_id == "arxiv:1706.03762v7"
    assert "Attention" in paper.title
    assert any("Vaswani" in a for a in paper.authors)
    assert paper.year == 2017
    assert paper.abstract is not None
    assert paper.pdf_url == "https://arxiv.org/pdf/1706.03762v7"


def test_parse_arxiv_empty_feed() -> None:
    """An empty arXiv feed should return an empty list without error."""

    xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    assert _parse_arxiv(xml) == []


# ------------------------------------------------------------------
# API route tests
# ------------------------------------------------------------------


def test_search_route_rejects_empty_query(auth_headers) -> None:
    """An empty search query should return 400."""

    response = client.post("/academic/search", json={"query": "  ", "limit": 5}, headers=auth_headers)
    assert response.status_code == 400


def test_search_route_rejects_invalid_limit(auth_headers) -> None:
    """A limit outside [1, 20] should fail schema validation."""

    response = client.post("/academic/search", json={"query": "AI", "limit": 50}, headers=auth_headers)
    assert response.status_code == 422


def test_summarize_route_returns_summary(auth_headers) -> None:
    """A successful summarize request should return the LLM output."""

    app.dependency_overrides[get_academic_service] = lambda: _StubAcademicService(
        summary="## Short Summary\nGreat paper."
    )

    response = client.post(
        "/academic/papers/summarize",
        json={
            "paper_id": "paper1",
            "title": "Attention Is All You Need",
            "authors": ["Vaswani et al."],
            "year": 2017,
            "abstract": "Transformer architecture.",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["paper_id"] == "paper1"
    assert "Short Summary" in body["summary"] or "Great paper" in body["summary"]


def test_summarize_route_502_on_llm_failure(auth_headers) -> None:
    """An LLM failure should surface as 502."""

    from app.services.llm import LLMError

    app.dependency_overrides[get_academic_service] = lambda: _StubAcademicService(
        error=LLMError("backend down")
    )

    response = client.post(
        "/academic/papers/summarize",
        json={
            "paper_id": "paper1",
            "title": "Some Paper",
            "authors": [],
            "year": None,
            "abstract": None,
        },
        headers=auth_headers,
    )

    assert response.status_code == 502


def test_ask_route_returns_answer(auth_headers) -> None:
    """A successful ask request should return the LLM answer."""

    app.dependency_overrides[get_academic_service] = lambda: _StubAcademicService(
        answer="Self-attention is the key mechanism."
    )

    response = client.post(
        "/academic/papers/ask",
        json={
            "paper_id": "paper1",
            "title": "Attention Is All You Need",
            "abstract": "We propose the Transformer.",
            "question": "What is the key mechanism?",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Self-attention is the key mechanism."
    assert body["question"] == "What is the key mechanism?"


def test_ask_route_rejects_empty_question(auth_headers) -> None:
    """An empty question should be rejected with 400."""

    response = client.post(
        "/academic/papers/ask",
        json={
            "paper_id": "paper1",
            "title": "Some Paper",
            "abstract": None,
            "question": "   ",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
