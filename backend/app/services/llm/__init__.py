"""LLM services: generate text completions from prompts."""

from app.core.config import settings
from app.services.llm.base import LLMService
from app.services.llm.gemini_api import GeminiLLMService
from app.services.llm.hf_api import HuggingFaceLLMService, LLMError


def create_llm_service() -> LLMService:
    """Return the LLM backend chosen by LLM_PROVIDER."""

    if settings.llm_provider.lower() == "huggingface":
        return HuggingFaceLLMService()
    return GeminiLLMService()


__all__ = [
    "LLMService",
    "GeminiLLMService",
    "HuggingFaceLLMService",
    "LLMError",
    "create_llm_service",
]
