"""Abstract interface for large language model services."""

from abc import ABC, abstractmethod


class LLMService(ABC):
    """Defines how a prompt is turned into a generated answer.

    Implementations may call a hosted API or a local model. Depending on this
    abstraction keeps the RAG pipeline decoupled from the LLM backend.
    """

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a completion for the given prompts.

        Args:
            system_prompt: Instructions that set the model's behavior.
            user_prompt: The user-facing content (context + question).

        Returns:
            The model's generated answer as plain text.
        """
