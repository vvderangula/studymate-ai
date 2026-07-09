"""HTTP routes for uploading PDF files."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.auth import get_current_user
from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.pdf_repository import PdfMetadataRepository
from app.schemas.pdf import (
    ChatRequest,
    ChatResponse,
    Citation,
    ProcessResponse,
    UploadResponse,
)
from app.services.chunk_storage import ChunkStorageService
from app.services.embeddings import EmbeddingError, HuggingFaceEmbeddingService
from app.services.llm import HuggingFaceLLMService, LLMError
from app.services.pdf_embedding_service import PdfEmbeddingService
from app.services.pdf_extractor import PDFExtractor
from app.services.pdf_processing_service import (
    ProcessingConfig,
    ProcessingError,
    ProcessingNotFoundError,
    ProcessingService,
)
from app.services.pdf_service import PdfService
from app.services.pdf_storage import PDFStorageService, PDFValidationError
from app.services.rag import (
    PdfNotFoundError,
    PdfNotProcessedError,
    PromptBuilder,
    RAGService,
)
from app.services.text_chunker import TextChunker
from app.services.vector_store import ChromaService, Retriever

router = APIRouter(prefix="/pdf", tags=["pdf"])
logger = logging.getLogger(__name__)

_storage = PDFStorageService()
_extractor = PDFExtractor()
_chunk_storage = ChunkStorageService()

_embeddings = HuggingFaceEmbeddingService()
_chroma = ChromaService()
_pdf_embedder = PdfEmbeddingService(
    _storage, _extractor, _chunk_storage, _embeddings, _chroma
)
_retriever = Retriever(_chroma, _embeddings)


def get_pdf_service() -> PdfService:
    """Provide a :class:`PdfService` wired with storage and repository."""

    return PdfService(PDFStorageService(), PdfMetadataRepository())


def get_processing_service() -> ProcessingService:
    """Provide a :class:`ProcessingService` with its pipeline dependencies."""

    return ProcessingService(
        ProcessingConfig(
            storage=PDFStorageService(),
            extractor=PDFExtractor(),
            chunker=TextChunker(),
            chunk_storage=ChunkStorageService(),
            repository=PdfMetadataRepository(),
        )
    )


def get_rag_service() -> RAGService:
    """Provide a :class:`RAGService` wired for cited PDF chat.

    Reuses the shared embedding and Chroma clients so models and the vector
    store connection are not reloaded on every request.
    """

    return RAGService(
        retriever=_retriever,
        prompt_builder=PromptBuilder(),
        llm=HuggingFaceLLMService(),
        indexer=_pdf_embedder,
        repository=PdfMetadataRepository(),
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_pdf(
    file: UploadFile = File(...),
    service: PdfService = Depends(get_pdf_service),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    """Accept, validate, store, and record a PDF file.

    Returns persisted metadata for the stored file. Rejects non-PDF,
    empty, corrupted, or oversized uploads with a 400 response.
    """

    try:
        record = service.upload(file, user_id=current_user.id)
    except PDFValidationError as exc:
        logger.warning("Rejected upload '%s': %s", file.filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    ActivityRepository().log(
        current_user.id,
        "pdf_uploaded",
        resource_id=record.id,
        resource_title=record.original_name,
    )
    logger.info(
        "Stored PDF '%s' as %s (%d bytes)",
        record.original_name,
        record.filename,
        record.size,
    )
    return UploadResponse(
        id=record.id,
        filename=record.filename,
        original_name=record.original_name,
        size=record.size,
        upload_time=record.upload_time,
        status=record.status,
        user_id=record.user_id,
    )


@router.post("/{file_id}/process", response_model=ProcessResponse)
def process_pdf(
    file_id: str,
    service: ProcessingService = Depends(get_processing_service),
    current_user: User = Depends(get_current_user),
) -> ProcessResponse:
    """Process a stored PDF into clean, chunked text.

    Runs the extraction, normalization, chunking, and local storage
    pipeline, updating the document's processing status. Responds with 404
    if the file is unknown or owned by another user, and 422 if processing
    fails (e.g. corrupted or scanned PDFs).
    """

    # Ownership: only process if the PDF belongs to the current user.
    pdf = PdfMetadataRepository().get(file_id)
    if pdf is None or (pdf.user_id is not None and pdf.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found.",
        )

    try:
        record = service.process(file_id)
    except ProcessingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ProcessingError as exc:
        logger.warning("Processing failed for %s: %s", file_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ProcessResponse(
        id=record.id,
        processing_status=record.processing_status,
        processed_at=record.processed_at,
        page_count=record.page_count,
        chunk_count=record.chunk_count,
    )


@router.post("/{file_id}/chat", response_model=ChatResponse)
def chat_with_pdf(
    file_id: str,
    request: ChatRequest,
    service: RAGService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Answer a question about a processed PDF with page citations.

    Ensures the PDF's chunks are embedded, retrieves the most relevant
    context, and generates a grounded answer. Responds with 400 for an empty
    question, 403 for a PDF not owned by the current user, 404 for an unknown
    PDF, 422 when the PDF has not been processed, and 502 if the embedding or
    LLM backend fails.
    """

    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )

    # Ownership: if the PDF exists and belongs to another user, deny.
    # Unknown file_ids are handled by the RAG service (returns 404).
    pdf = PdfMetadataRepository().get(file_id)
    if pdf is not None and pdf.user_id is not None and pdf.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    try:
        result = service.answer_with_citations(file_id, question)
    except PdfNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PdfNotProcessedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except (EmbeddingError, LLMError) as exc:
        logger.error("Chat failed for %s: %s", file_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    ActivityRepository().log(
        current_user.id,
        "pdf_chat",
        resource_id=file_id,
        resource_title=pdf.original_name if pdf is not None else None,
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
