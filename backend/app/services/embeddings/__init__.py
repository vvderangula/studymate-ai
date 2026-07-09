"""Embedding services: convert text into semantic vectors."""

from app.services.embeddings.base import EmbeddingService
from app.services.embeddings.hf_api import (
    EmbeddingError,
    HuggingFaceEmbeddingService,
)

__all__ = [
    "EmbeddingService",
    "HuggingFaceEmbeddingService",
    "EmbeddingError",
]
