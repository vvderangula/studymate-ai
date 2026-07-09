"""RAG orchestration: retrieve context, build a prompt, and call the LLM."""

import logging
from dataclasses import dataclass

from app.core.config import settings
from app.services.llm.base import LLMService
from app.services.pdf_embedding_service import PdfEmbeddingService
from app.services.rag.prompt_builder import PromptBuilder
from app.services.vector_store.retrieval import Retriever

logger = logging.getLogger(__name__)


class RagError(Exception):
    """Base error for the RAG pipeline."""


class PdfNotFoundError(RagError):
    """Raised when no PDF record exists for the requested identifier."""


class PdfNotProcessedError(RagError):
    """Raised when a PDF has no processed/embedded content to search."""


@dataclass(frozen=True)
class Citation:
    """A source reference for a grounded answer."""

    page: int | None
    chunk_id: str
    source_reference: str


@dataclass(frozen=True)
class RagResult:
    """An answer plus the citations and metadata that produced it."""

    answer: str
    citations: list[Citation]
    metadata: dict


class RAGService:
    """Coordinates retrieval, prompt building, and generation for PDF chat.

    Single responsibility: orchestrate the collaborators. It owns no retrieval
    or model logic itself, delegating to the injected components.
    """

    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm: LLMService,
        *,
        indexer: PdfEmbeddingService | None = None,
        repository=None,
    ) -> None:
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._llm = llm
        self._indexer = indexer
        self._repository = repository

    def answer(self, file_id: str, question: str) -> tuple[str, list[str]]:
        """Answer a question about a PDF using its indexed content.

        Args:
            file_id: Identifier of the source PDF.
            question: The user's question.

        Returns:
            A tuple of ``(answer, context_chunks)`` where the chunks are the
            excerpts used to ground the answer.
        """

        chunks = self._retriever.retrieve(file_id, question)
        system_prompt = self._prompt_builder.system_prompt()
        user_prompt = self._prompt_builder.user_prompt(chunks, question)

        answer = self._llm.generate(system_prompt, user_prompt)
        logger.info("Answered question for %s using %d chunks", file_id, len(chunks))
        return answer, chunks

    def answer_with_citations(self, file_id: str, question: str) -> RagResult:
        """Answer a question and return page-level citations and metadata.

        Pipeline: verify the PDF exists, ensure its chunks are embedded,
        retrieve the most relevant context, build a grounded prompt, generate
        an answer, and assemble citations from the retrieved metadata.

        Args:
            file_id: Identifier of the source PDF.
            question: The user's question.

        Returns:
            A :class:`RagResult` with the answer, citations, and metadata.

        Raises:
            PdfNotFoundError: If no record exists for ``file_id``.
            PdfNotProcessedError: If the PDF has no embedded content.
        """

        record = None
        if self._repository is not None:
            record = self._repository.get(file_id)
            if record is None:
                raise PdfNotFoundError("File not found.")

        if self._indexer is not None:
            indexed = self._indexer.ensure_indexed(file_id)
            if indexed == 0:
                raise PdfNotProcessedError(
                    "The PDF has not been processed yet. Process it before chatting."
                )

        top_k = settings.retrieval_top_k
        retrieved = self._retriever.retrieve_with_citations(file_id, question, top_k)

        system_prompt = self._prompt_builder.system_prompt()
        user_prompt = self._prompt_builder.user_prompt_cited(retrieved, question)
        answer = self._llm.generate(system_prompt, user_prompt)

        source_name = getattr(record, "original_name", None)
        citations = [
            Citation(
                page=chunk.page,
                chunk_id=chunk.chunk_id,
                source_reference=(
                    chunk.source_reference
                    or _source_reference(source_name, chunk.page)
                ),
            )
            for chunk in retrieved
        ]
        metadata = {
            "file_id": file_id,
            "chunks_retrieved": len(retrieved),
            "top_k": top_k,
        }
        logger.info(
            "Answered question for %s using %d cited chunks", file_id, len(retrieved)
        )
        return RagResult(answer=answer, citations=citations, metadata=metadata)


def _source_reference(source_name: str | None, page: int | None) -> str:
    """Build a human-readable source reference for a citation."""

    name = source_name or "document"
    if page is not None:
        return f"{name}, page {page}"
    return name

