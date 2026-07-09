"""Indexing: embed PDF chunks and store them in the vector database."""

import logging

from app.services.embeddings.base import EmbeddingService
from app.services.vector_store.chroma_service import ChromaService, collection_name

logger = logging.getLogger(__name__)


class IndexManager:
    """Stores PDF chunk embeddings in a per-document Chroma collection.

    Single responsibility: write side of the vector store. Embeddings are
    produced by an injected ``EmbeddingService`` so the indexer stays
    decoupled from the embedding backend.
    """

    def __init__(self, chroma: ChromaService, embeddings: EmbeddingService) -> None:
        self._chroma = chroma
        self._embeddings = embeddings

    def index_chunks(self, file_id: str, chunks: list[str]) -> int:
        """Embed and store the chunks of a PDF.

        Re-indexing the same ``file_id`` replaces any existing data so the
        operation is idempotent.

        Args:
            file_id: Identifier of the source PDF.
            chunks: Ordered text chunks to index.

        Returns:
            The number of chunks indexed.
        """

        if not chunks:
            return 0

        # Replace any prior index for this document to avoid duplicates.
        self._chroma.delete_collection(collection_name(file_id))
        collection = self._chroma.get_collection(collection_name(file_id))

        vectors = self._embeddings.embed_documents(chunks)
        ids = [f"{file_id}-{index}" for index in range(len(chunks))]
        metadatas = [
            {"file_id": file_id, "chunk_index": index} for index in range(len(chunks))
        ]

        collection.add(
            ids=ids,
            embeddings=vectors,
            documents=chunks,
            metadatas=metadatas,
        )
        logger.info("Indexed %d chunks for %s", len(chunks), file_id)
        return len(chunks)
