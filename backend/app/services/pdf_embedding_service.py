"""Application service that embeds processed PDF chunks into the vector store.

Runs after the processing pipeline: it loads the locally stored chunks for a
PDF, generates embeddings using the configured provider, and stores them in
ChromaDB with citation metadata (page number and chunk id). Embedding is
idempotent -- already embedded documents are skipped so vectors are never
duplicated and models are not invoked unnecessarily.
"""

import logging
import re

from app.repositories.chunk_repository import ChunkRepository
from app.services.embeddings.base import EmbeddingService
from app.services.pdf_extractor import PDFExtractionError, PDFExtractor
from app.services.pdf_storage import PDFStorageService
from app.services.vector_store.chroma_service import ChromaService

logger = logging.getLogger(__name__)

_WHITESPACE = re.compile(r"\s+")
_PREFIX_LEN = 60


def _collapse(text: str) -> str:
    """Collapse all runs of whitespace into single spaces."""

    return _WHITESPACE.sub(" ", text).strip()


class PdfEmbeddingService:
    """Embeds a PDF's stored chunks into ChromaDB with citation metadata.

    Single responsibility: turn processed chunks into stored vectors. The
    embedding provider is injected so the backend can be replaced without
    changing this service.
    """

    def __init__(
        self,
        storage: PDFStorageService,
        extractor: PDFExtractor,
        chunk_storage: ChunkRepository,
        embeddings: EmbeddingService,
        chroma: ChromaService,
    ) -> None:
        self._storage = storage
        self._extractor = extractor
        self._chunk_storage = chunk_storage
        self._embeddings = embeddings
        self._chroma = chroma

    def ensure_indexed(self, file_id: str) -> int:
        """Embed and store the PDF's chunks if not already indexed.

        Args:
            file_id: Identifier of a previously processed PDF.

        Returns:
            The number of vectors stored for the document. Returns ``0`` when
            no processed chunks exist for the file.
        """

        existing = self._chroma.count(file_id)
        if existing > 0:
            logger.info("Skipping embedding for %s: already indexed", file_id)
            return existing

        chunks = self._chunk_storage.load(file_id)
        if not chunks:
            return 0

        pages = self._page_numbers(file_id, chunks)
        vectors = self._embeddings.embed_documents(chunks)
        ids = [f"{file_id}-{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "file_id": file_id,
                "chunk_index": index,
                "chunk_id": ids[index],
                "page": pages[index],
            }
            for index in range(len(chunks))
        ]

        self._chroma.add_documents(
            file_id,
            ids=ids,
            embeddings=vectors,
            documents=chunks,
            metadatas=metadatas,
        )
        logger.info("Embedded %d chunks for %s", len(chunks), file_id)
        return len(chunks)

    def reindex(self, file_id: str) -> int:
        """Drop any existing vectors for the PDF and embed its chunks again.

        Called right after processing so chat never has to embed on the
        first question, and re-processing a PDF refreshes its index.
        """

        self._chroma.delete_document(file_id)
        return self.ensure_indexed(file_id)

    def _page_numbers(self, file_id: str, chunks: list[str]) -> list[int]:
        """Map each chunk to the source page it begins on.

        Best-effort: re-extracts per-page text and locates each chunk's
        leading text within a page. Falls back to page ``1`` when the source
        cannot be read or a chunk cannot be located.
        """

        path = self._storage.path_for(file_id)
        if path is None:
            return [1] * len(chunks)

        try:
            raw_pages = self._extractor.extract_pages(path)
        except PDFExtractionError:
            return [1] * len(chunks)

        collapsed_pages = [
            (index + 1, _collapse(text)) for index, text in enumerate(raw_pages)
        ]
        collapsed_pages = [(number, text) for number, text in collapsed_pages if text]
        if not collapsed_pages:
            return [1] * len(chunks)

        pages: list[int] = []
        cursor = 0
        for chunk in chunks:
            prefix = _collapse(chunk)[:_PREFIX_LEN]
            page_number = collapsed_pages[cursor][0]
            for position in range(cursor, len(collapsed_pages)):
                number, text = collapsed_pages[position]
                if prefix and prefix in text:
                    page_number = number
                    cursor = position
                    break
            pages.append(page_number)
        return pages
