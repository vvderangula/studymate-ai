"""Quiz generation built on the shared RAG components.

Reuses the existing ``Retriever`` (retrieval), ``PromptBuilder`` (prompting),
and ``LLMService`` (generation). It introduces no new retrieval or LLM
infrastructure; it only assembles a quiz-specific prompt and parses the
model's JSON response into structured questions.
"""

import json
import logging
import re
from dataclasses import dataclass

from app.core.config import settings
from app.services.llm.base import LLMService
from app.services.rag.prompt_builder import PromptBuilder
from app.services.study_tools.base import StudyToolsError, gather_context
from app.services.vector_store.retrieval import Retriever

logger = logging.getLogger(__name__)

_RETRIEVAL_QUERY = (
    "key concepts, definitions, facts, and important details for creating "
    "exam questions"
)


class QuizGenerationError(StudyToolsError):
    """Raised when the model output cannot be parsed into quiz questions."""


@dataclass(frozen=True)
class QuizQuestion:
    """A single generated quiz question."""

    type: str
    question: str
    options: list[str]
    correct_answer: str
    explanation: str


class QuizService:
    """Generates quizzes from a processed source using the RAG components."""

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
        question_type: str,
        difficulty: str,
        count: int,
        indexer=None,
        repository=None,
    ) -> list[QuizQuestion]:
        """Generate quiz questions grounded in a source's content.

        Args:
            source_id: Identifier of the PDF or YouTube source.
            question_type: ``mcq``, ``true_false``, or ``short_answer``.
            difficulty: ``easy``, ``medium``, or ``hard``.
            count: Number of questions to generate.
            indexer: Optional component exposing ``ensure_indexed(source_id)``.
            repository: Optional repository exposing ``get(source_id)``.

        Raises:
            SourceNotFoundError: If the source does not exist.
            SourceNotReadyError: If the source has no usable content.
            QuizGenerationError: If the model output cannot be parsed.
        """

        chunks = gather_context(
            self._retriever,
            source_id,
            _RETRIEVAL_QUERY,
            settings.study_tools_top_k,
            indexer=indexer,
            repository=repository,
        )

        system_prompt = self._prompt_builder.quiz_system_prompt()
        user_prompt = self._prompt_builder.quiz_user_prompt(
            chunks,
            question_type=question_type,
            difficulty=difficulty,
            count=count,
        )
        raw = self._llm.generate(system_prompt, user_prompt)
        questions = _parse_questions(raw, question_type)
        if not questions:
            raise QuizGenerationError("The model did not return any questions.")
        logger.info(
            "Generated %d %s quiz questions for %s",
            len(questions),
            question_type,
            source_id,
        )
        return questions


def _parse_questions(raw: str, question_type: str) -> list[QuizQuestion]:
    """Parse the model's JSON output into :class:`QuizQuestion` objects."""

    payload = _extract_json_array(raw)
    if payload is None:
        raise QuizGenerationError("The model returned an unparseable response.")

    questions: list[QuizQuestion] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        correct = str(item.get("correct_answer", "")).strip()
        if not question or not correct:
            continue
        options_raw = item.get("options") or []
        options = [str(option).strip() for option in options_raw if str(option).strip()]
        questions.append(
            QuizQuestion(
                type=question_type,
                question=question,
                options=options,
                correct_answer=correct,
                explanation=str(item.get("explanation", "")).strip(),
            )
        )
    return questions


def _extract_json_array(raw: str) -> list | None:
    """Best-effort extraction of a JSON array from model output."""

    text = raw.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return None
    return None
