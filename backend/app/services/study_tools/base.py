"""Shared helpers for the study-tools services (quiz and notes).

Both services reuse the existing retrieval, prompt-building, embedding, and
vector-store components. This module centralizes the source-preparation step
so neither service duplicates existence checks, on-demand indexing, or
retrieval logic.
"""

import logging

from app.services.vector_store.retrieval import Retriever

logger = logging.getLogger(__name__)


class StudyToolsError(Exception):
    """Base error for the study-tools services."""


class SourceNotFoundError(StudyToolsError):
    """Raised when no learning source exists for the requested identifier."""


class SourceNotReadyError(StudyToolsError):
    """Raised when a source has no processed/embedded content to use."""


def gather_context(
    retriever: Retriever,
    source_id: str,
    query: str,
    top_k: int,
    *,
    indexer=None,
    repository=None,
) -> list[str]:
    """Verify a source, ensure it is embedded, and retrieve its context.

    Reuses the shared ``Retriever`` and, when provided, the same indexer and
    repository used by the chat pipeline so no retrieval logic is duplicated.

    Args:
        retriever: The shared semantic retriever.
        source_id: Identifier of the PDF or YouTube source.
        query: The retrieval query used to gather relevant context.
        top_k: Number of chunks to retrieve.
        indexer: Optional component exposing ``ensure_indexed(source_id)``.
        repository: Optional repository exposing ``get(source_id)``.

    Returns:
        The retrieved context chunks, most relevant first.

    Raises:
        SourceNotFoundError: If the source does not exist.
        SourceNotReadyError: If the source has no usable content.
    """

    if repository is not None and repository.get(source_id) is None:
        raise SourceNotFoundError("Source not found.")

    if indexer is not None:
        indexed = indexer.ensure_indexed(source_id)
        if indexed == 0:
            raise SourceNotReadyError(
                "The source has not been processed yet. Process it first."
            )

    chunks = retriever.retrieve(source_id, query, top_k)
    if not chunks:
        raise SourceNotReadyError("No content is available for this source.")
    return chunks
