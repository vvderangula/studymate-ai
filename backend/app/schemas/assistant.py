"""Pydantic schemas for the AI Assistant general chat feature."""

from pydantic import BaseModel


class ChatTurn(BaseModel):
    """A single turn in a conversation (user or assistant message)."""

    role: str  # "user" | "assistant"
    content: str


class GeneralChatRequest(BaseModel):
    """A general chat request with optional conversation history for context."""

    message: str
    # Continue a saved conversation; omit to start a new one.
    conversation_id: str | None = None
    # Context for a brand-new conversation only (saved ones use stored messages).
    history: list[ChatTurn] = []


class GeneralChatResponse(BaseModel):
    """The assistant's reply to a general chat message."""

    answer: str
    conversation_id: str | None = None
    title: str | None = None
