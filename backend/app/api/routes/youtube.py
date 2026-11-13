"""HTTP routes for the Learn from YouTube module."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.conversation import KIND_YOUTUBE
from app.models.youtube import YoutubeMetadata
from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.youtube_repository import YoutubeMetadataRepository
from app.schemas.pdf import ChatRequest, ChatResponse, Citation
from app.schemas.history import MessageOut, MessagesResponse
from app.schemas.youtube import (
    ProcessYoutubeRequest,
    VideoItem,
    VideosResponse,
    YoutubeProcessResponse,
)
from app.repositories.chunk_repository import ChunkRepository
from app.services.embeddings import EmbeddingError, create_embedding_service
from app.services.llm import LLMError, create_llm_service
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

_chunk_storage = ChunkRepository()
_embeddings = create_embedding_service()
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
        llm=create_llm_service(),
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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

    # Records are per user, so an unscoped hit owned by someone else means
    # this user never processed the video.
    video_meta = YoutubeMetadataRepository(user_id=current_user.id).get(video_id)
    if video_meta is None and YoutubeMetadataRepository().get(video_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found.",
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The video has not been processed yet.",
        ) from exc
    except (EmbeddingError, LLMError) as exc:
        logger.error("Chat failed for %s: %s", video_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    conversations = ConversationRepository()
    conversation = conversations.get_or_create_for_source(
        current_user.id, KIND_YOUTUBE, video_id, video_meta.title if video_meta else "Video"
    )
    conversations.add_message(conversation, "user", question)
    conversations.add_message(
        conversation,
        "assistant",
        result.answer,
        [
            {
                "page": citation.page,
                "chunk_id": citation.chunk_id,
                "source_reference": citation.source_reference,
            }
            for citation in result.citations
        ],
    )

    ActivityRepository().log(
        current_user.id,
        "youtube_chat",
        resource_id=video_id,
        resource_title=video_meta.title if video_meta else None,
    )
    return ChatResponse(
        conversation_id=conversation.id,
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


def _owned_video(video_id: str, user: User) -> YoutubeMetadata:
    """The user's record of a video, otherwise a 404."""

    video = YoutubeMetadataRepository(user_id=user.id).get(video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")
    return video


@router.get("/videos", response_model=VideosResponse)
def list_videos(current_user: User = Depends(get_current_user)) -> VideosResponse:
    """The user's processed videos with chat counts, most recently active first."""

    conversations = {
        conversation.source_id: conversation
        for conversation in ConversationRepository().list(current_user.id, KIND_YOUTUBE, limit=500)
    }
    items = []
    for video in YoutubeMetadataRepository().list_by_user(current_user.id):
        conversation = conversations.get(video.video_id)
        moments = [video.created_at, video.processed_at,
                   conversation.updated_at if conversation else None]
        items.append(
            VideoItem(
                video_id=video.video_id,
                url=video.url,
                title=video.title,
                duration=video.duration,
                thumbnail=video.thumbnail,
                processed_at=video.processed_at,
                chunk_count=video.chunk_count,
                message_count=conversation.message_count if conversation else 0,
                last_active=max(filter(None, moments)),
            )
        )
    items.sort(key=lambda item: item.last_active, reverse=True)
    return VideosResponse(videos=items)


@router.get("/{video_id}/messages", response_model=MessagesResponse)
def get_messages(
    video_id: str, current_user: User = Depends(get_current_user)
) -> MessagesResponse:
    """The stored conversation about one video (empty if none yet)."""

    _owned_video(video_id, current_user)
    conversations = ConversationRepository()
    conversation = conversations.find_for_source(current_user.id, KIND_YOUTUBE, video_id)
    if conversation is None:
        return MessagesResponse(messages=[])
    return MessagesResponse(
        conversation_id=conversation.id,
        messages=[MessageOut.of(message) for message in conversations.messages(conversation.id)],
    )


@router.delete("/{video_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
def clear_messages(video_id: str, current_user: User = Depends(get_current_user)) -> None:
    """Clear the conversation about one video."""

    _owned_video(video_id, current_user)
    conversations = ConversationRepository()
    conversation = conversations.find_for_source(current_user.id, KIND_YOUTUBE, video_id)
    if conversation:
        conversations.clear(conversation.id, current_user.id)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: str, current_user: User = Depends(get_current_user)) -> None:
    """Remove a video from the user's library, with its conversation.

    The shared transcript index is kept while anyone else still has the video.
    """

    _owned_video(video_id, current_user)
    ConversationRepository().delete_for_source(current_user.id, KIND_YOUTUBE, video_id)
    YoutubeMetadataRepository().delete(current_user.id, video_id)
    if YoutubeMetadataRepository().get(video_id) is None:
        ChunkRepository().delete(video_id)
        _chroma.delete_document(video_id)
