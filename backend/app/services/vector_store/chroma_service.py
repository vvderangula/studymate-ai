"""ChromaDB client lifecycle and collection access."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from chromadb.api import ClientAPI
    from chromadb.api.models.Collection import Collection

logger = logging.getLogger(__name__)


def embedding_fingerprint() -> str:
    """Identify the configured embedding model and vector size."""

    if settings.embedding_provider.lower() == "huggingface":
        return f"huggingface:{settings.embedding_model_name}"
    return (
        f"gemini:{settings.gemini_embedding_model}:"
        f"{settings.gemini_embedding_dimensions}"
    )


def collection_name(file_id: str) -> str:
    """Return the Chroma collection name for a given PDF file id.

    The name carries a short hash of the embedding model, so switching models
    never mixes vectors of different sizes: the new model gets a fresh, empty
    collection and the document is re-embedded from its stored chunks.
    """

    suffix = hashlib.sha1(embedding_fingerprint().encode()).hexdigest()[:8]
    return f"pdf_{file_id}_{suffix}"


class ChromaService:
    """Owns a persistent ChromaDB client and exposes collection access.

    Single responsibility: manage the database connection. The client is
    created lazily so the heavy import and disk setup only happen when the
    vector store is actually used.
    """

    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = persist_dir or settings.chroma_dir
        self._client: ClientAPI | None = None

    def get_collection(self, name: str) -> Collection:
        """Return an existing collection or create it if absent."""

        return self._get_client().get_or_create_collection(name=name)

    def delete_collection(self, name: str) -> None:
        """Delete a collection if it exists; a no-op otherwise."""

        try:
            self._get_client().delete_collection(name=name)
        except Exception:  # noqa: BLE001 - deletion of a missing collection is fine
            logger.debug("Collection '%s' not found for deletion", name)

    def add_documents(
        self,
        file_id: str,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Add document vectors to a PDF's collection."""

        collection = self.get_collection(collection_name(file_id))
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def update_documents(
        self,
        file_id: str,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Insert or replace document vectors in a PDF's collection."""

        collection = self.get_collection(collection_name(file_id))
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        file_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> dict:
        """Return the ``top_k`` nearest documents for a query vector."""

        collection = self.get_collection(collection_name(file_id))
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

    def count(self, file_id: str) -> int:
        """Return the number of vectors stored for a PDF."""

        collection = self.get_collection(collection_name(file_id))
        return collection.count()

    def delete_document(self, file_id: str) -> None:
        """Delete all vectors for a PDF by dropping its collection."""

        self.delete_collection(collection_name(file_id))

    def _get_client(self) -> ClientAPI:
        """Create and cache the persistent Chroma client on first use."""

        if self._client is None:
            import chromadb

            Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
            logger.info("Opening Chroma store at '%s'", self._persist_dir)
            self._client = chromadb.PersistentClient(path=self._persist_dir)
        return self._client
