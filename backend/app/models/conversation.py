"""Domain models for stored conversations."""

from dataclasses import dataclass, field
from datetime import datetime

# Which part of the app a conversation belongs to.
KIND_PDF = "pdf"
KIND_YOUTUBE = "youtube"
KIND_ASSISTANT = "assistant"
KIND_PAPER = "paper"


@dataclass(frozen=True)
class Conversation:
    """A thread of messages.

    PDF, YouTube and paper conversations are tied to one source
    (``source_id``); assistant conversations are free-standing.
    """

    id: str
    user_id: str
    kind: str
    title: str
    created_at: datetime
    updated_at: datetime
    source_id: str | None = None
    message_count: int = 0
    preview: str = ""


@dataclass(frozen=True)
class Message:
    """One message in a conversation."""

    id: str
    conversation_id: str
    role: str  # "user" | "assistant"
    text: str
    created_at: datetime
    citations: list[dict] = field(default_factory=list)
