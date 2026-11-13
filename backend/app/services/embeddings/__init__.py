"""Embedding services: convert text into semantic vectors."""

from app.core.config import settings
from app.services.embeddings.base import EmbeddingService
from app.services.embeddings.gemini_api import GeminiEmbeddingService
from app.services.embeddings.hf_api import (
    EmbeddingError,
    HuggingFaceEmbeddingService,
)


def create_embedding_service() -> EmbeddingService:
    """Return the embedding backend chosen by EMBEDDING_PROVIDER."""

    if settings.embedding_provider.lower() == "huggingface":
        return HuggingFaceEmbeddingService()
    return GeminiEmbeddingService()


__all__ = [
    "EmbeddingService",
    "GeminiEmbeddingService",
    "HuggingFaceEmbeddingService",
    "EmbeddingError",
    "create_embedding_service",
]
