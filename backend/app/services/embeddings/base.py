"""Abstract interface for embedding services."""

from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    """Defines how text is converted into embedding vectors.

    Implementations may use a local model or a remote API. Depending on this
    abstraction (rather than a concrete class) keeps the rest of the system
    decoupled from the embedding backend.
    """

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents.

        Args:
            texts: The document chunks to embed.

        Returns:
            One embedding vector per input text, in the same order.
        """

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string and return its vector."""
