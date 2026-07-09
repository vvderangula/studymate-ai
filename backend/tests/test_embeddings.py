"""Unit tests for the Hugging Face embedding service."""

import httpx
import pytest

from app.services.embeddings.hf_api import (
    EmbeddingError,
    HuggingFaceEmbeddingService,
)


class _FakeResponse:
    """Minimal stand-in for an httpx.Response."""

    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


def test_embed_documents_empty_returns_empty_without_api_call() -> None:
    """An empty input should short-circuit without contacting the API."""

    service = HuggingFaceEmbeddingService(model_name="m", api_key="key")

    assert service.embed_documents([]) == []


def test_embed_documents_returns_vectors(monkeypatch) -> None:
    """A successful response should be returned as a list of vectors."""

    vectors = [[0.1, 0.2], [0.3, 0.4]]
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: _FakeResponse(vectors)
    )
    service = HuggingFaceEmbeddingService(model_name="m", api_key="key")

    result = service.embed_documents(["a", "b"])

    assert result == vectors


def test_embed_query_returns_single_vector(monkeypatch) -> None:
    """embed_query should return the first vector of the batch response."""

    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: _FakeResponse([[0.5, 0.6]])
    )
    service = HuggingFaceEmbeddingService(model_name="m", api_key="key")

    assert service.embed_query("hello") == [0.5, 0.6]


def test_missing_api_key_raises() -> None:
    """A missing API key should raise an EmbeddingError."""

    service = HuggingFaceEmbeddingService(model_name="m", api_key="")

    with pytest.raises(EmbeddingError):
        service.embed_query("hello")


def test_http_error_is_wrapped(monkeypatch) -> None:
    """Transport errors should be normalized to EmbeddingError."""

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", _raise)
    service = HuggingFaceEmbeddingService(model_name="m", api_key="key")

    with pytest.raises(EmbeddingError):
        service.embed_documents(["a"])
