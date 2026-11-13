"""HTTP routes for the AI Study Tools module (quiz and notes)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.study_repository import NoteRepository, QuizRepository
from app.repositories.pdf_repository import PdfMetadataRepository
from app.repositories.youtube_repository import YoutubeMetadataRepository
from app.schemas.study_tools import (
    Difficulty,
    NoteType,
    QuestionType,
    NotesRequest,
    NotesResponse,
    QuizQuestionResponse,
    QuizRequest,
    QuizResponse,
    SourceItem,
    SourcesResponse,
    StudyHistoryItem,
    StudyHistoryResponse,
    SourceType,
)
from app.repositories.chunk_repository import ChunkRepository
from app.services.embeddings import EmbeddingError, create_embedding_service
from app.services.llm import LLMError, create_llm_service
from app.services.pdf_embedding_service import PdfEmbeddingService
from app.services.pdf_extractor import PDFExtractor
from app.services.pdf_storage import PDFStorageService
from app.services.rag import PromptBuilder
from app.services.study_tools import (
    NotesService,
    QuizGenerationError,
    QuizService,
    SourceNotFoundError,
    SourceNotReadyError,
    UnknownNoteTypeError,
)
from app.services.text_chunker import TextChunker
from app.services.vector_store import ChromaService, Retriever
from app.services.youtube import YoutubeProcessingService, YoutubeTranscriptService

router = APIRouter(prefix="/study-tools", tags=["study-tools"])
logger = logging.getLogger(__name__)

_storage = PDFStorageService()
_extractor = PDFExtractor()
_chunk_storage = ChunkRepository()
_embeddings = create_embedding_service()
_chroma = ChromaService()
_retriever = Retriever(_chroma, _embeddings)
_prompt_builder = PromptBuilder()

# Reused indexers so processed sources are embedded on demand exactly as the
# chat pipeline does, without duplicating any embedding logic.
_pdf_indexer = PdfEmbeddingService(
    _storage, _extractor, _chunk_storage, _embeddings, _chroma
)
_youtube_indexer = YoutubeProcessingService(
    YoutubeTranscriptService(),
    TextChunker(),
    _chunk_storage,
    _embeddings,
    _chroma,
    YoutubeMetadataRepository(),
)


def _indexer_and_repository(source_type: SourceType, user_id: str):
    """Return the indexer and repository for the given source type."""

    if source_type is SourceType.youtube:
        return _youtube_indexer, YoutubeMetadataRepository(user_id=user_id)
    return _pdf_indexer, PdfMetadataRepository()


def _source_title(record) -> str:
    """Display name of a PDF or video record."""

    return getattr(record, "original_name", None) or getattr(record, "title", "") or ""


class _UserScopedRepository:
    """Restrict source lookup to records owned by the authenticated user."""

    def __init__(self, repository, user_id: str) -> None:
        self._repository = repository
        self._user_id = user_id

    def get(self, source_id: str):
        record = self._repository.get(source_id)
        if record is None:
            return None
        if getattr(record, "user_id", None) != self._user_id:
            return None
        return record


def get_quiz_service() -> QuizService:
    """Provide a :class:`QuizService` wired with the shared RAG components."""

    return QuizService(_retriever, _prompt_builder, create_llm_service())


def get_notes_service() -> NotesService:
    """Provide a :class:`NotesService` wired with the shared RAG components."""

    return NotesService(_retriever, _prompt_builder, create_llm_service())


@router.get("/sources", response_model=SourcesResponse)
def list_sources(current_user: User = Depends(get_current_user)) -> SourcesResponse:
    """List processed PDFs and YouTube videos owned by the current user."""

    sources: list[SourceItem] = []
    for pdf in PdfMetadataRepository().list_by_user(current_user.id):
        sources.append(
            SourceItem(id=pdf.id, type=SourceType.pdf, title=pdf.original_name)
        )
    for video in YoutubeMetadataRepository().list_by_user(current_user.id):
        sources.append(
            SourceItem(id=video.video_id, type=SourceType.youtube, title=video.title)
        )
    return SourcesResponse(sources=sources)


@router.post("/quiz", response_model=QuizResponse)
def generate_quiz(
    request: QuizRequest,
    service: QuizService = Depends(get_quiz_service),
    current_user: User = Depends(get_current_user),
) -> QuizResponse:
    """Generate a quiz from a processed source.

    Responds with 404 for an unknown source, 422 when the source has no
    usable content or the quiz could not be generated, and 502 if the
    embedding or LLM backend fails.
    """

    indexer, repository = _indexer_and_repository(request.source_type, current_user.id)
    scoped_repository = _UserScopedRepository(repository, current_user.id)

    try:
        questions = service.generate(
            request.source_id,
            question_type=request.question_type.value,
            difficulty=request.difficulty.value,
            count=request.count,
            indexer=indexer,
            repository=scoped_repository,
        )
    except SourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (SourceNotReadyError, QuizGenerationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except (EmbeddingError, LLMError) as exc:
        logger.error("Quiz generation failed for %s: %s", request.source_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    saved = QuizRepository().save(
        user_id=current_user.id,
        source_type=request.source_type.value,
        source_id=request.source_id,
        source_title=_source_title(scoped_repository.get(request.source_id)),
        question_type=request.question_type.value,
        difficulty=request.difficulty.value,
        count=request.count,
        questions=[
            {
                "type": question.type,
                "question": question.question,
                "options": question.options,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
            }
            for question in questions
        ],
    )
    quiz_response = _quiz_response(saved)
    ActivityRepository().log(current_user.id, "quiz_generated", resource_id=request.source_id)
    return quiz_response


@router.post("/notes", response_model=NotesResponse)
def generate_notes(
    request: NotesRequest,
    service: NotesService = Depends(get_notes_service),
    current_user: User = Depends(get_current_user),
) -> NotesResponse:
    """Generate study notes from a processed source.

    Responds with 404 for an unknown source, 422 when the source has no
    usable content, and 502 if the embedding or LLM backend fails.
    """

    indexer, repository = _indexer_and_repository(request.source_type, current_user.id)
    scoped_repository = _UserScopedRepository(repository, current_user.id)

    try:
        content = service.generate(
            request.source_id,
            note_type=request.note_type.value,
            indexer=indexer,
            repository=scoped_repository,
        )
    except SourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (SourceNotReadyError, UnknownNoteTypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except (EmbeddingError, LLMError) as exc:
        logger.error("Notes generation failed for %s: %s", request.source_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    saved = NoteRepository().save(
        user_id=current_user.id,
        source_type=request.source_type.value,
        source_id=request.source_id,
        source_title=_source_title(scoped_repository.get(request.source_id)),
        note_type=request.note_type.value,
        content=content,
    )
    ActivityRepository().log(current_user.id, "notes_generated", resource_id=request.source_id)
    return _notes_response(saved)


_QUESTION_TYPE_LABEL = {
    "mcq": "Multiple choice",
    "true_false": "True / false",
    "short_answer": "Short answer",
}
_NOTE_TYPE_LABEL = {
    "chapter_summary": "Chapter summary",
    "key_points": "Key points",
    "important_concepts": "Important concepts",
    "formula_sheet": "Formula sheet",
    "revision_notes": "Revision notes",
}


def _quiz_response(quiz) -> QuizResponse:
    return QuizResponse(
        id=quiz.id,
        source_id=quiz.source_id,
        source_type=SourceType(quiz.source_type),
        source_title=quiz.source_title,
        question_type=QuestionType(quiz.question_type),
        difficulty=Difficulty(quiz.difficulty),
        created_at=quiz.created_at,
        questions=[QuizQuestionResponse(**question) for question in quiz.questions],
    )


def _notes_response(note) -> NotesResponse:
    return NotesResponse(
        id=note.id,
        source_id=note.source_id,
        source_type=SourceType(note.source_type),
        source_title=note.source_title,
        note_type=NoteType(note.note_type),
        content=note.content,
        created_at=note.created_at,
    )


@router.get("/history", response_model=StudyHistoryResponse)
def study_history(current_user: User = Depends(get_current_user)) -> StudyHistoryResponse:
    """Every saved quiz and note set, newest first."""

    items = [
        StudyHistoryItem(
            id=quiz.id,
            kind="quiz",
            source_type=SourceType(quiz.source_type),
            source_id=quiz.source_id,
            source_title=quiz.source_title,
            created_at=quiz.created_at,
            label=(
                f"{_QUESTION_TYPE_LABEL.get(quiz.question_type, quiz.question_type)}, "
                f"{quiz.difficulty}, {len(quiz.questions)} questions"
            ),
        )
        for quiz in QuizRepository().list(current_user.id)
    ] + [
        StudyHistoryItem(
            id=note.id,
            kind="notes",
            source_type=SourceType(note.source_type),
            source_id=note.source_id,
            source_title=note.source_title,
            created_at=note.created_at,
            label=_NOTE_TYPE_LABEL.get(note.note_type, note.note_type),
        )
        for note in NoteRepository().list(current_user.id)
    ]
    items.sort(key=lambda item: item.created_at, reverse=True)
    return StudyHistoryResponse(items=items)


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
def get_quiz(quiz_id: str, current_user: User = Depends(get_current_user)) -> QuizResponse:
    """Reopen a saved quiz."""

    quiz = QuizRepository().get(quiz_id, current_user.id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    return _quiz_response(quiz)


@router.delete("/quizzes/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(quiz_id: str, current_user: User = Depends(get_current_user)) -> None:
    """Delete a saved quiz."""

    if not QuizRepository().delete(quiz_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")


@router.get("/notes/{note_id}", response_model=NotesResponse)
def get_notes(note_id: str, current_user: User = Depends(get_current_user)) -> NotesResponse:
    """Reopen saved notes."""

    note = NoteRepository().get(note_id, current_user.id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notes not found.")
    return _notes_response(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notes(note_id: str, current_user: User = Depends(get_current_user)) -> None:
    """Delete saved notes."""

    if not NoteRepository().delete(note_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notes not found.")
