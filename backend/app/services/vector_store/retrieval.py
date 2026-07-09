"""Retrieval: find the most relevant PDF chunks for a query."""

import logging
from dataclasses import dataclass

from app.core.config import settings
from app.services.embeddings.base import EmbeddingService
from app.services.vector_store.chroma_service import ChromaService, collection_name

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    """A retrieved chunk with the metadata needed for citations."""

    text: str
    chunk_id: str
    chunk_index: int
    page: int | None = None
    distance: float | None = None
    source_reference: str | None = None


class Retriever:
    """Performs semantic search over a document's indexed chunks.

    Single responsibility: read side of the vector store. The query is
    embedded with the same ``EmbeddingService`` used for indexing to keep the
    vector spaces consistent.
    """

    def __init__(self, chroma: ChromaService, embeddings: EmbeddingService) -> None:
        self._chroma = chroma
        self._embeddings = embeddings

    def retrieve(
        self,
        file_id: str,
        query: str,
        top_k: int | None = None,
    ) -> list[str]:
        """Return the ``top_k`` chunks most relevant to ``query``.

        Args:
            file_id: Identifier of the source PDF to search within.
            query: The user's question or search text.
            top_k: Number of chunks to return; defaults to the configured value.

        Returns:
            The matching chunk texts, ordered from most to least relevant.
        """

        normalized = query.strip()
        if not normalized:
            return []

        limit = top_k or settings.retrieval_top_k
        vector = self._embeddings.embed_query(normalized)

        collection = self._chroma.get_collection(collection_name(file_id))
        result = collection.query(query_embeddings=[vector], n_results=limit)

        documents = result.get("documents") or [[]]
        logger.info("Retrieved %d chunks for %s", len(documents[0]), file_id)
        return documents[0]

    def retrieve_with_citations(
        self,
        file_id: str,
        query: str,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Return the ``top_k`` most relevant chunks with citation metadata.

        Args:
            file_id: Identifier of the source PDF to search within.
            query: The user's question or search text.
            top_k: Number of chunks to return; defaults to the configured value.

        Returns:
            Retrieved chunks (text plus page and chunk-id metadata), ordered
            from most to least relevant.
        """

        normalized = query.strip()
        if not normalized:
            return []

        limit = top_k or settings.retrieval_top_k
        vector = self._embeddings.embed_query(normalized)
        result = self._chroma.search(file_id, vector, limit)

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for index, document in enumerate(documents):
            meta = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            page = meta.get("page")
            reference = meta.get("source_reference")
            chunks.append(
                RetrievedChunk(
                    text=document,
                    chunk_id=str(meta.get("chunk_id", f"{file_id}-{index}")),
                    chunk_index=int(meta.get("chunk_index", index)),
                    page=int(page) if page is not None else None,
                    distance=distance,
                    source_reference=str(reference) if reference is not None else None,
                )
            )
        logger.info("Retrieved %d cited chunks for %s", len(chunks), file_id)
        return chunks

