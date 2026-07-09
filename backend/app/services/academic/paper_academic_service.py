"""Summarizes academic papers and answers questions using the shared AI pipeline.

Reuses PromptBuilder (for prompts) and LLMService (for generation). No
vector-store retrieval is used because only abstract-level text is available;
the abstract itself acts as the context, keeping the pipeline consistent with
the existing PromptBuilder + LLM pattern.
"""

import logging

from app.services.llm.base import LLMService
from app.services.rag.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class PaperSummaryError(Exception):
    """Raised when paper summarization or Q&A fails."""


class PaperAcademicService:
    """Generates summaries of and answers questions about academic papers.

    Delegates prompt construction to the shared :class:`PromptBuilder` and
    text generation to the injected :class:`LLMService`. No new AI pipeline
    is introduced.
    """

    def __init__(self, prompt_builder: PromptBuilder, llm: LLMService) -> None:
        self._prompt_builder = prompt_builder
        self._llm = llm

    def summarize(
        self,
        title: str,
        authors: list[str],
        year: int | None,
        abstract: str | None,
    ) -> str:
        """Generate a structured Markdown summary of a paper.

        Args:
            title: Paper title.
            authors: List of author names.
            year: Publication year, or ``None`` if unknown.
            abstract: Paper abstract text, or ``None`` if unavailable.

        Returns:
            A Markdown string with Short Summary, Key Contributions,
            Important Findings, and Conclusion sections.
        """

        context = _build_paper_context(title, authors, year, abstract)
        system_prompt = self._prompt_builder.academic_summary_system_prompt()
        user_prompt = self._prompt_builder.academic_summary_user_prompt(context)
        result = self._llm.generate(system_prompt, user_prompt)
        logger.info("Generated summary for paper: %r", title[:60])
        return result.strip()

    def ask(
        self,
        title: str,
        abstract: str | None,
        question: str,
    ) -> str:
        """Answer a question about a paper using its abstract as context.

        Reuses the shared system prompt and :meth:`PromptBuilder.user_prompt`
        so the generation call is identical to the existing chat pipeline.

        Args:
            title: Paper title (included in context for grounding).
            abstract: Paper abstract used as the retrieval context.
            question: User's question about the paper.

        Returns:
            The LLM-generated answer string.
        """

        context = (
            f"Title: {title}\n\n{abstract}"
            if abstract
            else f"Title: {title}\n\n(Abstract not available.)"
        )
        system_prompt = self._prompt_builder.system_prompt()
        user_prompt = self._prompt_builder.user_prompt([context], question)
        return self._llm.generate(system_prompt, user_prompt).strip()


def _build_paper_context(
    title: str,
    authors: list[str],
    year: int | None,
    abstract: str | None,
) -> str:
    """Format paper metadata into a context block for prompting."""

    author_str = ", ".join(authors) if authors else "Unknown"
    year_str = str(year) if year else "Unknown"
    abstract_str = abstract if abstract else "(Abstract not available.)"
    return (
        f"Title: {title}\n"
        f"Authors: {author_str}\n"
        f"Year: {year_str}\n\n"
        f"Abstract:\n{abstract_str}"
    )
