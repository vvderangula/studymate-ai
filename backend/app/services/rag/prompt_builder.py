"""Builds grounded prompts from retrieved context and a user question."""

from app.services.vector_store.retrieval import RetrievedChunk

SYSTEM_PROMPT = (
    "You are StudyMate AI, a helpful study assistant. Answer the user's "
    "question using only the provided context from their document. If the "
    "answer is not contained in the context, say you could not find it in "
    "the document. Be concise and accurate."
)

QUIZ_SYSTEM_PROMPT = (
    "You are StudyMate AI, an expert exam author. Using only the provided "
    "context, write clear, accurate quiz questions. Base every question and "
    "answer strictly on the context. Respond with valid JSON only, following "
    "the requested schema exactly, and never include commentary or markdown "
    "outside the JSON."
)

NOTES_SYSTEM_PROMPT = (
    "You are StudyMate AI, an expert study-notes writer. Using only the "
    "provided context, produce well-structured, accurate study notes in "
    "GitHub-flavored Markdown. Base the notes strictly on the context and be "
    "concise, organized, and easy to revise from."
)

_QUESTION_TYPE_INSTRUCTIONS = {
    "mcq": (
        "Write multiple-choice questions. Each question must have exactly four "
        "distinct options, and the correct_answer must exactly match one option."
    ),
    "true_false": (
        "Write True/False questions. The options must be [\"True\", \"False\"], "
        "and the correct_answer must be either \"True\" or \"False\"."
    ),
    "short_answer": (
        "Write short-answer questions. Omit the options field (use an empty "
        "list), and provide a concise model answer in correct_answer."
    ),
}


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

    def quiz_system_prompt(self) -> str:
        """Return the system instruction for quiz generation."""

        return QUIZ_SYSTEM_PROMPT

    def quiz_user_prompt(
        self,
        context_chunks: list[str],
        *,
        question_type: str,
        difficulty: str,
        count: int,
    ) -> str:
        """Build the user prompt for generating a quiz from context.

        Args:
            context_chunks: Relevant document excerpts, most relevant first.
            question_type: One of ``mcq``, ``true_false``, or ``short_answer``.
            difficulty: One of ``easy``, ``medium``, or ``hard``.
            count: Number of questions to generate.

        Returns:
            A prompt instructing the model to emit a JSON array of questions.
        """

        context = _join_context(context_chunks)
        instruction = _QUESTION_TYPE_INSTRUCTIONS.get(
            question_type, _QUESTION_TYPE_INSTRUCTIONS["mcq"]
        )
        return (
            f"Context:\n{context}\n\n"
            f"Task: Generate {count} {difficulty}-difficulty quiz questions "
            f"based only on the context above.\n{instruction}\n\n"
            "Return a JSON array where each element is an object with the keys: "
            '"question" (string), "options" (array of strings, empty if not '
            'applicable), "correct_answer" (string), and "explanation" (string '
            "explaining why the answer is correct). Return only the JSON array."
        )

    def notes_system_prompt(self) -> str:
        """Return the system instruction for notes generation."""

        return NOTES_SYSTEM_PROMPT

    def notes_user_prompt(
        self,
        context_chunks: list[str],
        *,
        note_type: str,
    ) -> str:
        """Build the user prompt for generating study notes from context.

        Args:
            context_chunks: Relevant document excerpts, most relevant first.
            note_type: A human-readable notes format (e.g. "Chapter Summary").

        Returns:
            A prompt instructing the model to emit Markdown notes.
        """

        context = _join_context(context_chunks)
        return (
            f"Context:\n{context}\n\n"
            f"Task: Produce \"{note_type}\" study notes based only on the "
            "context above. Use clear Markdown with headings, bullet points, "
            "and tables where helpful. If the requested notes are not "
            "applicable to the context, say so briefly in Markdown."
        )


def _join_context(context_chunks: list[str]) -> str:
    """Join context chunks into a numbered block for prompting."""

    if not context_chunks:
        return "(no relevant context found)"
    return "\n\n".join(
        f"[{index + 1}] {chunk}" for index, chunk in enumerate(context_chunks)
    )

