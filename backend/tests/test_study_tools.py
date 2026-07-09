"""Tests for the AI Study Tools module (quiz and notes)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.api.routes.study_tools import get_notes_service, get_quiz_service
from app.main import app
from app.services.rag.prompt_builder import PromptBuilder
from app.services.study_tools import (
    NotesService,
    QuizGenerationError,
    QuizService,
    SourceNotFoundError,
    SourceNotReadyError,
    UnknownNoteTypeError,
)

client = TestClient(app)


class _FakeRetriever:
    """Returns a fixed set of context chunks."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks
        self.calls: list[tuple[str, str, int]] = []

    def retrieve(self, source_id: str, query: str, top_k=None) -> list[str]:
        self.calls.append((source_id, query, top_k))
        return self._chunks


class _FakeLLM:
    """Returns a canned completion and records the prompts."""

    def __init__(self, output: str) -> None:
        self._output = output
        self.system_prompt = ""
        self.user_prompt = ""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self._output


class _FakeIndexer:
    def __init__(self, indexed: int) -> None:
        self._indexed = indexed
        self.calls: list[str] = []

    def ensure_indexed(self, source_id: str) -> int:
        self.calls.append(source_id)
        return self._indexed


class _FakeRepository:
    def __init__(self, record) -> None:
        self._record = record

    def get(self, source_id: str):
        return self._record


_MCQ_JSON = json.dumps(
    [
        {
            "question": "What is 2 + 2?",
            "options": ["3", "4", "5", "6"],
            "correct_answer": "4",
            "explanation": "Two plus two is four.",
        },
        {
            "question": "What is the capital of France?",
            "options": ["Paris", "Rome", "Berlin", "Madrid"],
            "correct_answer": "Paris",
            "explanation": "Paris is the capital of France.",
        },
    ]
)


# --- QuizService ----------------------------------------------------------


def test_quiz_service_parses_questions() -> None:
    """The quiz service should parse the model's JSON into questions."""

    retriever = _FakeRetriever(["alpha", "beta"])
    service = QuizService(retriever, PromptBuilder(), _FakeLLM(_MCQ_JSON))

    questions = service.generate(
        "file1",
        question_type="mcq",
        difficulty="easy",
        count=2,
        indexer=_FakeIndexer(2),
        repository=_FakeRepository(object()),
    )

    assert len(questions) == 2
    assert questions[0].correct_answer == "4"
    assert questions[0].options == ["3", "4", "5", "6"]
    assert questions[0].explanation


def test_quiz_service_handles_json_wrapped_in_text() -> None:
    """A JSON array embedded in extra prose should still be parsed."""

    wrapped = f"Here is your quiz:\n{_MCQ_JSON}\nGood luck!"
    service = QuizService(_FakeRetriever(["alpha"]), PromptBuilder(), _FakeLLM(wrapped))

    questions = service.generate(
        "file1", question_type="mcq", difficulty="easy", count=2
    )

    assert len(questions) == 2


def test_quiz_service_missing_source_raises() -> None:
    """An unknown source should raise SourceNotFoundError."""

    service = QuizService(_FakeRetriever(["alpha"]), PromptBuilder(), _FakeLLM("[]"))

    with pytest.raises(SourceNotFoundError):
        service.generate(
            "missing",
            question_type="mcq",
            difficulty="easy",
            count=5,
            repository=_FakeRepository(None),
        )


def test_quiz_service_unindexed_source_raises() -> None:
    """A source with no embedded content should raise SourceNotReadyError."""

    service = QuizService(_FakeRetriever(["alpha"]), PromptBuilder(), _FakeLLM("[]"))

    with pytest.raises(SourceNotReadyError):
        service.generate(
            "file1",
            question_type="mcq",
            difficulty="easy",
            count=5,
            indexer=_FakeIndexer(0),
        )


def test_quiz_service_unparseable_output_raises() -> None:
    """Non-JSON model output should raise a generation error."""

    service = QuizService(
        _FakeRetriever(["alpha"]), PromptBuilder(), _FakeLLM("not json at all")
    )

    with pytest.raises(QuizGenerationError):
        service.generate("file1", question_type="mcq", difficulty="easy", count=5)


# --- NotesService ---------------------------------------------------------


def test_notes_service_returns_markdown() -> None:
    """The notes service should return the model's Markdown output."""

    llm = _FakeLLM("# Summary\n\n- point one\n- point two")
    service = NotesService(_FakeRetriever(["alpha", "beta"]), PromptBuilder(), llm)

    content = service.generate("file1", note_type="key_points")

    assert content.startswith("# Summary")
    assert "point one" in content


def test_notes_service_unknown_type_raises() -> None:
    """An unsupported note type should raise UnknownNoteTypeError."""

    service = NotesService(_FakeRetriever(["alpha"]), PromptBuilder(), _FakeLLM("x"))

    with pytest.raises(UnknownNoteTypeError):
        service.generate("file1", note_type="does_not_exist")


# --- API routes -----------------------------------------------------------


class _StubQuizService:
    def __init__(self, questions=None, error: Exception | None = None) -> None:
        self._questions = questions or []
        self._error = error

    def generate(self, source_id: str, **kwargs):
        if self._error is not None:
            raise self._error
        return self._questions


class _StubNotesService:
    def __init__(self, content: str = "", error: Exception | None = None) -> None:
        self._content = content
        self._error = error

    def generate(self, source_id: str, **kwargs) -> str:
        if self._error is not None:
            raise self._error
        return self._content


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_sources_route_lists_processed(monkeypatch, auth_headers) -> None:
    """The sources route should combine processed PDFs and videos."""

    from app.api.routes import study_tools as routes
    from app.models.pdf import PdfMetadata
    from app.models.youtube import YoutubeMetadata

    pdf = PdfMetadata(
        id="pdf1",
        filename="pdf1.pdf",
        original_name="Notes.pdf",
        size=10,
        upload_time=None,
        status="uploaded",
        processing_status="completed",
    )
    video = YoutubeMetadata(
        video_id="vid1",
        url="https://youtu.be/vid1",
        title="Lecture 1",
        processing_status="completed",
    )

    class _PdfRepo:
        def list_by_user(self, user_id):
            return [pdf]

    class _YtRepo:
        def list_by_user(self, user_id):
            return [video]

    monkeypatch.setattr(routes, "PdfMetadataRepository", lambda: _PdfRepo())
    monkeypatch.setattr(routes, "YoutubeMetadataRepository", lambda: _YtRepo())

    response = client.get("/study-tools/sources", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    ids = {item["id"]: item["type"] for item in body["sources"]}
    assert ids == {"pdf1": "pdf", "vid1": "youtube"}


def test_quiz_route_returns_questions(auth_headers) -> None:
    """A successful quiz request returns the generated questions."""

    from app.services.study_tools.quiz_service import QuizQuestion

    questions = [
        QuizQuestion(
            type="mcq",
            question="Q1?",
            options=["a", "b", "c", "d"],
            correct_answer="a",
            explanation="because",
        )
    ]
    app.dependency_overrides[get_quiz_service] = lambda: _StubQuizService(questions)

    response = client.post(
        "/study-tools/quiz",
        json={
            "source_id": "pdf1",
            "source_type": "pdf",
            "question_type": "mcq",
            "difficulty": "easy",
            "count": 5,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["questions"][0]["question"] == "Q1?"
    assert body["questions"][0]["correct_answer"] == "a"


def test_quiz_route_unknown_source_returns_404(auth_headers) -> None:
    """An unknown source should surface as a 404."""

    app.dependency_overrides[get_quiz_service] = lambda: _StubQuizService(
        error=SourceNotFoundError("Source not found.")
    )

    response = client.post(
        "/study-tools/quiz",
        json={
            "source_id": "missing",
            "source_type": "pdf",
            "question_type": "mcq",
            "difficulty": "easy",
            "count": 5,
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_quiz_route_rejects_invalid_count(auth_headers) -> None:
    """An unsupported question count should fail schema validation."""

    response = client.post(
        "/study-tools/quiz",
        json={
            "source_id": "pdf1",
            "source_type": "pdf",
            "question_type": "mcq",
            "difficulty": "easy",
            "count": 7,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_notes_route_returns_content(auth_headers) -> None:
    """A successful notes request returns the generated Markdown."""

    app.dependency_overrides[get_notes_service] = lambda: _StubNotesService(
        content="# Notes"
    )

    response = client.post(
        "/study-tools/notes",
        json={
            "source_id": "vid1",
            "source_type": "youtube",
            "note_type": "chapter_summary",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["content"] == "# Notes"


def test_notes_route_not_ready_returns_422(auth_headers) -> None:
    """A source without usable content should surface as a 422."""

    app.dependency_overrides[get_notes_service] = lambda: _StubNotesService(
        error=SourceNotReadyError("No content is available for this source.")
    )

    response = client.post(
        "/study-tools/notes",
        json={
            "source_id": "vid1",
            "source_type": "youtube",
            "note_type": "key_points",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422
