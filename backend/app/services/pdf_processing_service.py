"""Application service orchestrating the PDF processing pipeline.

Pipeline: validate stored file -> extract per-page text -> normalize
whitespace -> remove empty pages -> split into chunks -> store chunks
locally -> update processing status. This service does not generate
embeddings, connect to a vector database, or perform retrieval.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.pdf import PdfMetadata
from app.repositories.pdf_repository import PdfMetadataRepository
from app.repositories.chunk_repository import ChunkRepository
from app.services.pdf_extractor import PDFExtractionError, PDFExtractor
from app.services.pdf_storage import PDFStorageService
from app.services.text_chunker import TextChunker

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

_WHITESPACE_RUN = re.compile(r"[ \t]+")


class ProcessingError(Exception):
    """Raised when a stored PDF cannot be processed."""


class ProcessingNotFoundError(ProcessingError):
    """Raised when no stored PDF exists for the given identifier."""


@dataclass(frozen=True)
class ProcessingConfig:
    """Grouped dependencies for the processing pipeline."""

    storage: PDFStorageService
    extractor: PDFExtractor
    chunker: TextChunker
    chunk_storage: ChunkRepository
    repository: PdfMetadataRepository


class ProcessingService:
    """Coordinates extraction, cleaning, chunking, and status tracking."""

    def __init__(self, config: ProcessingConfig) -> None:
        self._storage = config.storage
        self._extractor = config.extractor
        self._chunker = config.chunker
        self._chunk_storage = config.chunk_storage
        self._repository = config.repository

    def process(self, file_id: str) -> PdfMetadata:
        """Run the processing pipeline for a stored PDF.

        Args:
            file_id: Identifier of a previously uploaded PDF.

        Returns:
            The updated :class:`PdfMetadata` with completed status.

        Raises:
            ProcessingNotFoundError: If no record exists for ``file_id``.
            ProcessingError: If the file is missing, corrupted, or yields
                no extractable text or chunks.
        """

        record = self._repository.get(file_id)
        if record is None:
            raise ProcessingNotFoundError("File not found.")

        path = self._storage.path_for(file_id)
        if path is None:
            self._mark_failed(file_id)
            raise ProcessingError("Stored file is missing.")

        try:
            raw_pages = self._extractor.extract_pages(path)
        except PDFExtractionError as exc:
            self._mark_failed(file_id)
            logger.warning("Processing failed for %s: %s", file_id, exc)
            raise ProcessingError("The PDF is corrupted or could not be read.") from exc

        pages = [self._normalize(page) for page in raw_pages]
        non_empty_pages = [page for page in pages if page]
        if not non_empty_pages:
            self._mark_failed(file_id)
            raise ProcessingError(
                "No extractable text found. The PDF may be scanned or image-only."
            )

        text = "\n\n".join(non_empty_pages)
        chunks = self._chunker.chunk(text)
        if not chunks:
            self._mark_failed(file_id)
            raise ProcessingError("No text chunks could be generated.")

        self._chunk_storage.save(file_id, chunks)
        self._repository.update_processing(
            file_id,
            processing_status=STATUS_COMPLETED,
            processed_at=datetime.now(timezone.utc),
            page_count=len(non_empty_pages),
            chunk_count=len(chunks),
        )

        updated = self._repository.get(file_id)
        if updated is None:  # pragma: no cover - record just confirmed present
            raise ProcessingError("File not found.")
        logger.info(
            "Processed %s: %d pages, %d chunks",
            file_id,
            len(non_empty_pages),
            len(chunks),
        )
        return updated

    def _mark_failed(self, file_id: str) -> None:
        """Record a failed processing attempt for ``file_id``."""

        self._repository.update_processing(
            file_id,
            processing_status=STATUS_FAILED,
            processed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _normalize(text: str) -> str:
        """Collapse whitespace within a page's text.

        Normalizes line endings, collapses runs of spaces and tabs, drops
        blank lines, and joins the remaining lines into clean single-spaced
        text. Returns an empty string for pages with no content.
        """

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = (_WHITESPACE_RUN.sub(" ", line).strip() for line in text.split("\n"))
        return " ".join(line for line in lines if line).strip()
