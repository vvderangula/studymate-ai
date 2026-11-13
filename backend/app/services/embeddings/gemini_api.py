"""Google Gemini embedding service (REST, no extra SDK)."""

import logging
import math

import httpx

from app.core.config import settings
from app.services.gemini_http import post_with_retry
from app.services.embeddings.base import EmbeddingService
from app.services.embeddings.hf_api import EmbeddingError

logger = logging.getLogger(__name__)

_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:batchEmbedContents"
)

# Gemini accepts at most 100 texts per batchEmbedContents call.
_BATCH_SIZE = 100


class GeminiEmbeddingService(EmbeddingService):
    """Generates embeddings via the Gemini API (gemini-embedding-001 by default).

    Documents and queries use the matching retrieval task types, and vectors
    are L2-normalised so Chroma's default distance ranks them correctly.
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        dimensions: int | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._model_name = model_name or settings.gemini_embedding_model
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._dimensions = dimensions or settings.gemini_embedding_dimensions
        self._timeout = timeout

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents into vectors."""

        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            vectors.extend(self._request(batch, "RETRIEVAL_DOCUMENT"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string into a vector."""

        return self._request([text], "RETRIEVAL_QUERY")[0]

    def _request(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Call batchEmbedContents and return normalised vectors."""

        if not self._api_key:
            raise EmbeddingError("GEMINI_API_KEY is not configured.")
        if not texts:
            return []

        model_ref = f"models/{self._model_name}"
        payload = {
            "requests": [
                {
                    "model": model_ref,
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                    "outputDimensionality": self._dimensions,
                }
                for text in texts
            ]
        }
        try:
            response = post_with_retry(
                _API_URL.format(model=self._model_name),
                api_key=self._api_key,
                payload=payload,
                timeout=self._timeout,
            )
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Gemini embedding API returned %s: %s",
                exc.response.status_code,
                exc.response.text[:300],
            )
            raise EmbeddingError(
                f"Embedding API error ({exc.response.status_code})."
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Gemini embedding request failed: %s", exc)
            raise EmbeddingError("Failed to reach the embedding service.") from exc

        try:
            vectors = [item["values"] for item in data["embeddings"]]
        except (KeyError, TypeError) as exc:
            raise EmbeddingError("Unexpected embedding response shape.") from exc
        if len(vectors) != len(texts):
            raise EmbeddingError("Unexpected embedding response shape.")
        return [_normalise(vector) for vector in vectors]


def _normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector
