"""Pydantic schemas for stored conversations and messages."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.conversation import Conversation, Message
from app.schemas.pdf import Citation


class MessageOut(BaseModel):
    """One stored message."""

    id: str
    role: str
    text: str
    created_at: datetime
    citations: list[Citation] = Field(default_factory=list)

    @classmethod
    def of(cls, message: Message) -> "MessageOut":
        return cls(
            id=message.id,
            role=message.role,
            text=message.text,
            created_at=message.created_at,
            citations=[Citation(**citation) for citation in message.citations],
        )


class ConversationSummary(BaseModel):
    """A conversation as shown in a history list."""

    id: str
    kind: str
    title: str
    source_id: str | None = None
    message_count: int
    preview: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, conversation: Conversation) -> "ConversationSummary":
        return cls(
            id=conversation.id,
            kind=conversation.kind,
            title=conversation.title,
            source_id=conversation.source_id,
            message_count=conversation.message_count,
            preview=conversation.preview,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


class ConversationDetail(ConversationSummary):
    """A conversation with all of its messages."""

    messages: list[MessageOut]


class MessagesResponse(BaseModel):
    """The stored messages for a source (PDF, video, paper)."""

    conversation_id: str | None = None
    messages: list[MessageOut]
