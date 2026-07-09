"""Builds grounded prompts from retrieved context and a user question."""

from app.services.vector_store.retrieval import RetrievedChunk

SYSTEM_PROMPT = (
    "You are StudyMate AI, a helpful study assistant. Answer the user's "
    "question using only the provided context from their document. If the "
    "answer is not contained in the context, say you could not find it in "
    "the document. Be concise and accurate."
)


class PromptBuilder:
    """Assembles the system and user prompts for a RAG request.

    Single responsibility: turn retrieved chunks plus a question into the
    exact text sent to the LLM.
    """

    def system_prompt(self) -> str:
        """Return the system instruction that grounds the model."""

        return SYSTEM_PROMPT

    def user_prompt(self, context_chunks: list[str], question: str) -> str:
        """Combine context chunks and the question into a user prompt.

        Args:
            context_chunks: Relevant document excerpts, most relevant first.
            question: The user's question.

        Returns:
            A formatted prompt containing the context and the question.
        """

        if context_chunks:
            context = "\n\n".join(
                f"[{index + 1}] {chunk}" for index, chunk in enumerate(context_chunks)
            )
        else:
            context = "(no relevant context found)"

        return f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

    def user_prompt_cited(
        self,
        chunks: list[RetrievedChunk],
        question: str,
    ) -> str:
        """Build a user prompt whose context is labelled with page numbers.

        Args:
            chunks: Retrieved chunks carrying page metadata, most relevant first.
            question: The user's question.

        Returns:
            A formatted prompt that lets the model reference source pages.
        """

        if chunks:
            context = "\n\n".join(
                f"[{index + 1}] (page {chunk.page}) {chunk.text}"
                for index, chunk in enumerate(chunks)
            )
        else:
            context = "(no relevant context found)"

        return f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

