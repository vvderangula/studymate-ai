"""Hugging Face Inference API embedding service."""

import logging

import httpx

from app.core.config import settings
from app.services.embeddings.base import EmbeddingService

logger = logging.getLogger(__name__)

_API_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "{model}/pipeline/feature-extraction"
)


class EmbeddingError(Exception):
    """Raised when the embedding backend fails to return vectors."""


class HuggingFaceEmbeddingService(EmbeddingService):
    """Generates embeddings via the Hugging Face Inference API.

    Uses the configured API key and model name. Keeps no heavy local
    dependencies, calling the hosted feature-extraction endpoint over HTTP.
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._model_name = model_name or settings.embedding_model_name
        self._api_key = api_key if api_key is not None else settings.hf_api_key
        self._timeout = timeout

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents into vectors."""

        if not texts:
            return []
        result = self._request(texts)
        if not isinstance(result, list) or len(result) != len(texts):
            raise EmbeddingError("Unexpected embedding response shape.")
        return result

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string into a vector."""

        return self.embed_documents([text])[0]

    def _request(self, texts: list[str]) -> list[list[float]]:
        """Call the Inference API and return the raw embedding vectors."""

        if not self._api_key:
            raise EmbeddingError("HF_API_KEY is not configured.")

        url = _API_URL.format(model=self._model_name)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"inputs": texts}

        try:
            response = httpx.post(
                url, headers=headers, json=payload, timeout=self._timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Embedding API returned %s: %s",
                exc.response.status_code,
                exc.response.text[:300],
            )
            raise EmbeddingError(
                f"Embedding API error ({exc.response.status_code})."
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Embedding request failed: %s", exc)
            raise EmbeddingError("Failed to reach the embedding service.") from exc
