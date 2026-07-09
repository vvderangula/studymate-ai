"""HTTP routes for the AI Study Tools module (quiz and notes).

Both generators reuse the shared retrieval, prompt-building, embedding,
vector-store, and LLM components. Sources may be processed PDFs or processed
YouTube videos; retrieval is identical for both, so only the existence check
and on-demand indexing differ by source type.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.repositories.pdf_repository import PdfMetadataRepository
from app.repositories.youtube_repository import YoutubeMetadataRepository
from app.schemas.study_tools import (
    NotesRequest,
    NotesResponse,
    QuizQuestionResponse,
    QuizRequest,
    QuizResponse,
    SourceItem,
    SourcesResponse,
    SourceType,
)
from app.services.chunk_storage import ChunkStorageService
from app.services.embeddings import EmbeddingError, HuggingFaceEmbeddingService
from app.services.llm import HuggingFaceLLMService, LLMError
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
_chunk_storage = ChunkStorageService()
_embeddings = HuggingFaceEmbeddingService()
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


def _indexer_and_repository(source_type: SourceType):
    """Return the indexer and repository for the given source type."""

    if source_type is SourceType.youtube:
        return _youtube_indexer, YoutubeMetadataRepository()
    return _pdf_indexer, PdfMetadataRepository()


def get_quiz_service() -> QuizService:
    """Provide a :class:`QuizService` wired with the shared RAG components."""

    return QuizService(_retriever, _prompt_builder, HuggingFaceLLMService())


def get_notes_service() -> NotesService:
    """Provide a :class:`NotesService` wired with the shared RAG components."""

    return NotesService(_retriever, _prompt_builder, HuggingFaceLLMService())


@router.get("/sources", response_model=SourcesResponse)
def list_sources() -> SourcesResponse:
    """List processed PDFs and YouTube videos available for generation."""

    sources: list[SourceItem] = []
    for pdf in PdfMetadataRepository().list_processed():
        sources.append(
            SourceItem(id=pdf.id, type=SourceType.pdf, title=pdf.original_name)
        )
    for video in YoutubeMetadataRepository().list_processed():
        sources.append(
            SourceItem(id=video.video_id, type=SourceType.youtube, title=video.title)
        )
    return SourcesResponse(sources=sources)


@router.post("/quiz", response_model=QuizResponse)
def generate_quiz(
    request: QuizRequest,
    service: QuizService = Depends(get_quiz_service),
) -> QuizResponse:
    """Generate a quiz from a processed source.

    Responds with 404 for an unknown source, 422 when the source has no
    usable content or the quiz could not be generated, and 502 if the
    embedding or LLM backend fails.
    """

    indexer, repository = _indexer_and_repository(request.source_type)

    try:
        questions = service.generate(
            request.source_id,
            question_type=request.question_type.value,
            difficulty=request.difficulty.value,
            count=request.count,
            indexer=indexer,
            repository=repository,
        )
    except SourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (SourceNotReadyError, QuizGenerationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except (EmbeddingError, LLMError) as exc:
        logger.error("Quiz generation failed for %s: %s", request.source_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return QuizResponse(
        source_id=request.source_id,
        source_type=request.source_type,
        question_type=request.question_type,
        difficulty=request.difficulty,
        questions=[
            QuizQuestionResponse(
                type=question.type,
                question=question.question,
                options=question.options,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            )
            for question in questions
        ],
    )


@router.post("/notes", response_model=NotesResponse)
def generate_notes(
    request: NotesRequest,
    service: NotesService = Depends(get_notes_service),
) -> NotesResponse:
    """Generate study notes from a processed source.

    Responds with 404 for an unknown source, 422 when the source has no
    usable content, and 502 if the embedding or LLM backend fails.
    """

    indexer, repository = _indexer_and_repository(request.source_type)

    try:
        content = service.generate(
            request.source_id,
            note_type=request.note_type.value,
            indexer=indexer,
            repository=repository,
        )
    except SourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (SourceNotReadyError, UnknownNoteTypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except (EmbeddingError, LLMError) as exc:
        logger.error("Notes generation failed for %s: %s", request.source_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return NotesResponse(
        source_id=request.source_id,
        source_type=request.source_type,
        note_type=request.note_type,
        content=content,
    )
