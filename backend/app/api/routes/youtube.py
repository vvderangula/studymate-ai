"""HTTP routes for the Learn from YouTube module."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.youtube_repository import YoutubeMetadataRepository
from app.schemas.pdf import ChatRequest, ChatResponse, Citation
from app.schemas.youtube import ProcessYoutubeRequest, YoutubeProcessResponse
from app.services.chunk_storage import ChunkStorageService
from app.services.embeddings import EmbeddingError, HuggingFaceEmbeddingService
from app.services.llm import HuggingFaceLLMService, LLMError
from app.services.rag import (
    PdfNotFoundError,
    PdfNotProcessedError,
    PromptBuilder,
    RAGService,
)
from app.services.text_chunker import TextChunker
from app.services.vector_store import ChromaService, Retriever
from app.services.youtube import (
    InvalidYoutubeUrlError,
    TranscriptUnavailableError,
    YoutubeProcessingError,
    YoutubeProcessingService,
    YoutubeTranscriptService,
)

router = APIRouter(prefix="/youtube", tags=["youtube"])
logger = logging.getLogger(__name__)

_chunk_storage = ChunkStorageService()
_embeddings = HuggingFaceEmbeddingService()
_chroma = ChromaService()
_youtube_processor = YoutubeProcessingService(
    YoutubeTranscriptService(),
    TextChunker(),
    _chunk_storage,
    _embeddings,
    _chroma,
    YoutubeMetadataRepository(),
)
_retriever = Retriever(_chroma, _embeddings)


def get_youtube_processor() -> YoutubeProcessingService:
    """Provide the shared YouTube processing service."""

    return _youtube_processor


def get_rag_service() -> RAGService:
    """Provide a :class:`RAGService` wired for cited YouTube chat.

    Reuses the shared embedding and Chroma clients and the shared RAG
    pipeline. The processor doubles as the indexer so already-embedded
    transcripts are recognized, and the repository supplies existence checks.
    """

    return RAGService(
        retriever=_retriever,
        prompt_builder=PromptBuilder(),
        llm=HuggingFaceLLMService(),
        indexer=_youtube_processor,
        repository=YoutubeMetadataRepository(),
    )


@router.post("/process", response_model=YoutubeProcessResponse)
def process_youtube(
    request: ProcessYoutubeRequest,
    service: YoutubeProcessingService = Depends(get_youtube_processor),
    current_user: User = Depends(get_current_user),
) -> YoutubeProcessResponse:
    """Retrieve and process a YouTube video's transcript.

    Validates the URL, fetches the transcript, and runs it through the shared
    chunking, embedding, and vector-store pipeline. Responds with 400 for an
    invalid URL and 422 when no transcript is available or usable.
    """

    try:
        record = service.process(request.url, user_id=current_user.id)
    except InvalidYoutubeUrlError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (TranscriptUnavailableError, YoutubeProcessingError) as exc:
        logger.info("YouTube processing failed for '%s': %s", request.url, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except EmbeddingError as exc:
        logger.error("Embedding failed for '%s': %s", request.url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    ActivityRepository().log(
        current_user.id,
        "youtube_processed",
        resource_id=record.video_id,
        resource_title=record.title,
    )
    return YoutubeProcessResponse(
        video_id=record.video_id,
        title=record.title,
        duration=record.duration,
        thumbnail=record.thumbnail,
        processing_status=record.processing_status,
        processed_at=record.processed_at,
        chunk_count=record.chunk_count,
    )


@router.post("/{video_id}/chat", response_model=ChatResponse)
def chat_with_youtube(
    video_id: str,
    request: ChatRequest,
    service: RAGService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Answer a question about a processed video with timestamp citations.

    Retrieves the most relevant transcript context and generates a grounded
    answer. Responds with 400 for an empty question, 404 for an unknown
    video, 422 when the video has not been processed, and 502 if the
    embedding or LLM backend fails.
    """

    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )

    try:
        result = service.answer_with_citations(video_id, question)
    except PdfNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found.",
        ) from exc
    except PdfNotProcessedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The video has not been processed yet.",
        ) from exc
    except (EmbeddingError, LLMError) as exc:
        logger.error("Chat failed for %s: %s", video_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    video_meta = YoutubeMetadataRepository().get(video_id)
    ActivityRepository().log(
        current_user.id,
        "youtube_chat",
        resource_id=video_id,
        resource_title=video_meta.title if video_meta else None,
    )
    return ChatResponse(
        answer=result.answer,
        citations=[
            Citation(
                page=citation.page,
                chunk_id=citation.chunk_id,
                source_reference=citation.source_reference,
            )
            for citation in result.citations
        ],
        metadata=result.metadata,
    )
