"""Pydantic schemas for the AI Study Tools (quiz and notes) feature."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Supported learning-source types."""

    pdf = "pdf"
    youtube = "youtube"


class SourceItem(BaseModel):
    """A processed learning source available for study-tool generation."""

    id: str
    type: SourceType
    title: str


class SourcesResponse(BaseModel):
    """The list of processed sources a user can generate from."""

    sources: list[SourceItem]


class QuestionType(str, Enum):
    """Supported quiz question formats."""

    mcq = "mcq"
    true_false = "true_false"
    short_answer = "short_answer"


class Difficulty(str, Enum):
    """Supported quiz difficulty levels."""

    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuizRequest(BaseModel):
    """A request to generate a quiz from a processed source."""

    source_id: str
    source_type: SourceType
    question_type: QuestionType
    difficulty: Difficulty
    count: Literal[5, 10, 20] = 5


class QuizQuestionResponse(BaseModel):
    """A single generated quiz question."""

    type: str
    question: str
    options: list[str] = Field(default_factory=list)
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    """A generated quiz for a source."""

    source_id: str
    source_type: SourceType
    question_type: QuestionType
    difficulty: Difficulty
    questions: list[QuizQuestionResponse]


class NoteType(str, Enum):
    """Supported study-note formats."""

    chapter_summary = "chapter_summary"
    key_points = "key_points"
    important_concepts = "important_concepts"
    formula_sheet = "formula_sheet"
    revision_notes = "revision_notes"


class NotesRequest(BaseModel):
    """A request to generate study notes from a processed source."""

    source_id: str
    source_type: SourceType
    note_type: NoteType


class NotesResponse(BaseModel):
    """Generated Markdown notes for a source."""

    source_id: str
    source_type: SourceType
    note_type: NoteType
    content: str
