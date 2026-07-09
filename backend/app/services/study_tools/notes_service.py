"""Notes generation built on the shared RAG components.

Reuses the existing ``Retriever`` (retrieval), ``PromptBuilder`` (prompting),
and ``LLMService`` (generation). It introduces no new retrieval system; it
only assembles a notes-specific prompt for a chosen note format and returns
the generated Markdown.
"""

import logging

from app.core.config import settings
from app.services.llm.base import LLMService
from app.services.rag.prompt_builder import PromptBuilder
from app.services.study_tools.base import StudyToolsError, gather_context
from app.services.vector_store.retrieval import Retriever

logger = logging.getLogger(__name__)

# Maps a note-type key to its display label and a retrieval query tuned to
# surface the most relevant context for that kind of notes.
_NOTE_TYPES: dict[str, tuple[str, str]] = {
    "chapter_summary": (
        "Chapter Summary",
        "overview and summary of the main topics, sections, and chapters",
    ),
    "key_points": (
        "Key Points",
        "key points, main ideas, and most important takeaways",
    ),
    "important_concepts": (
        "Important Concepts",
        "important concepts, definitions, and key terminology",
    ),
    "formula_sheet": (
        "Formula Sheet",
        "formulas, equations, symbols, and numerical relationships",
    ),
    "revision_notes": (
        "Revision Notes",
        "concise revision notes and highlights for exam preparation",
    ),
}


class UnknownNoteTypeError(StudyToolsError):
    """Raised when an unsupported note type is requested."""


class NotesService:
    """Generates study notes from a processed source using RAG components."""

    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm: LLMService,
    ) -> None:
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._llm = llm

    def generate(
        self,
        source_id: str,
        *,
        note_type: str,
        indexer=None,
        repository=None,
    ) -> str:
        """Generate Markdown study notes grounded in a source's content.

        Args:
            source_id: Identifier of the PDF or YouTube source.
            note_type: One of the supported note-type keys.
            indexer: Optional component exposing ``ensure_indexed(source_id)``.
            repository: Optional repository exposing ``get(source_id)``.

        Returns:
            The generated notes as a Markdown string.

        Raises:
            UnknownNoteTypeError: If ``note_type`` is not supported.
            SourceNotFoundError: If the source does not exist.
            SourceNotReadyError: If the source has no usable content.
        """

        if note_type not in _NOTE_TYPES:
            raise UnknownNoteTypeError(f"Unsupported note type: {note_type}")

        label, query = _NOTE_TYPES[note_type]
        chunks = gather_context(
            self._retriever,
            source_id,
            query,
            settings.study_tools_top_k,
            indexer=indexer,
            repository=repository,
        )

        system_prompt = self._prompt_builder.notes_system_prompt()
        user_prompt = self._prompt_builder.notes_user_prompt(chunks, note_type=label)
        notes = self._llm.generate(system_prompt, user_prompt).strip()
        logger.info("Generated '%s' notes for %s", note_type, source_id)
        return notes
