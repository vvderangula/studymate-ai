"""Domain models for saved study-tool outputs."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SavedQuiz:
    """A generated quiz, kept so it can be reopened."""

    id: str
    user_id: str
    source_type: str
    source_id: str
    source_title: str
    question_type: str
    difficulty: str
    count: int
    created_at: datetime
    questions: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class SavedNote:
    """Generated study notes (Markdown), kept so they can be reopened."""

    id: str
    user_id: str
    source_type: str
    source_id: str
    source_title: str
    note_type: str
    content: str
    created_at: datetime
