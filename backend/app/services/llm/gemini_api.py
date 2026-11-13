"""Google Gemini chat LLM service (REST, no extra SDK)."""

import logging

import httpx

from app.core.config import settings
from app.services.gemini_http import post_with_retry
from app.services.llm.base import LLMService
from app.services.llm.hf_api import LLMError

logger = logging.getLogger(__name__)

_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)


class GeminiLLMService(LLMService):
    """Generates answers via the Gemini generateContent API."""

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._model_name = model_name or settings.gemini_llm_model
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._max_tokens = max_tokens or settings.llm_max_tokens
        self._temperature = (
            temperature if temperature is not None else settings.llm_temperature
        )
        self._timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate an answer for the given system and user prompts."""

        if not self._api_key:
            raise LLMError("GEMINI_API_KEY is not configured.")

        generation_config: dict = {
            "maxOutputTokens": self._max_tokens,
            "temperature": self._temperature,
        }
        # 2.5-series models "think" by default and those tokens count against
        # maxOutputTokens, which can leave the visible answer empty.
        if "2.5" in self._model_name:
            generation_config["thinkingConfig"] = {"thinkingBudget": 0}

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
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
                "Gemini LLM API returned %s: %s",
                exc.response.status_code,
                exc.response.text[:300],
            )
            raise LLMError(
                f"LLM API error ({exc.response.status_code})."
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Gemini LLM request failed: %s", exc)
            raise LLMError("Failed to generate a response.") from exc

        return self._parse_answer(data)

    @staticmethod
    def _parse_answer(data: dict) -> str:
        """Join the text parts of the first candidate."""

        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            reason = (data.get("promptFeedback") or {}).get("blockReason")
            if reason:
                raise LLMError(f"Gemini blocked the prompt ({reason}).") from exc
            raise LLMError("Unexpected LLM response shape.") from exc

        text = "".join(
            part.get("text", "") for part in parts if not part.get("thought")
        ).strip()
        if not text:
            raise LLMError("The model returned an empty answer.")
        return text
