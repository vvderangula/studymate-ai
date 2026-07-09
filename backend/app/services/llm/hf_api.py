"""Hugging Face chat-completion LLM service."""

import logging

import httpx

from app.core.config import settings
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

_API_URL = "https://router.huggingface.co/v1/chat/completions"


class LLMError(Exception):
    """Raised when the LLM backend fails to return a completion."""


class HuggingFaceLLMService(LLMService):
    """Generates answers via the Hugging Face router chat-completions API.

    Uses the configured API key and model name. The endpoint is
    OpenAI-compatible, so requests follow the standard ``messages`` schema.
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._model_name = model_name or settings.llm_model_name
        self._api_key = api_key if api_key is not None else settings.hf_api_key
        self._max_tokens = max_tokens or settings.llm_max_tokens
        self._temperature = (
            temperature if temperature is not None else settings.llm_temperature
        )
        self._timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate an answer for the given system and user prompts."""

        if not self._api_key:
            raise LLMError("HF_API_KEY is not configured.")

        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            response = httpx.post(
                _API_URL, headers=headers, json=payload, timeout=self._timeout
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("LLM request failed: %s", exc)
            raise LLMError("Failed to generate a response.") from exc

        return self._parse_answer(data)

    @staticmethod
    def _parse_answer(data: dict) -> str:
        """Extract the assistant message text from an API response."""

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected LLM response shape.") from exc
