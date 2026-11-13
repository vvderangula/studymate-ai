"""HTTP routes for the AI Assistant: saved general-chat conversations."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.conversation import KIND_ASSISTANT
from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.assistant import ChatTurn, GeneralChatRequest, GeneralChatResponse
from app.schemas.history import ConversationDetail, ConversationSummary, MessageOut
from app.services.llm import LLMError, create_llm_service

router = APIRouter(prefix="/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are StudyMate AI, a helpful and knowledgeable study assistant. "
    "Answer the user's questions clearly, accurately, and concisely. "
    "You may discuss any educational topic."
)
_HISTORY_TURNS = 10  # recent turns sent back to the model as context
_TITLE_CHARS = 60


@router.post("/chat", response_model=GeneralChatResponse)
def general_chat(
    request: GeneralChatRequest,
    current_user: User = Depends(get_current_user),
) -> GeneralChatResponse:
    """Reply to a message and save both sides of the exchange.

    With ``conversation_id`` the reply continues that saved conversation and
    its stored messages are the context. Without one, a new conversation is
    started (titled from the first message); a client-supplied ``history`` is
    then used as context. Responds with 400 for an empty message, 404 for an
    unknown conversation and 502 if the LLM backend fails.
    """

    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must not be empty.",
        )

    conversations = ConversationRepository()
    conversation = None
    history = request.history
    if request.conversation_id:
        conversation = conversations.get(request.conversation_id, current_user.id)
        if conversation is None or conversation.kind != KIND_ASSISTANT:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
            )
        history = [
            ChatTurn(role=stored.role, content=stored.text)
            for stored in conversations.messages(conversation.id, limit=_HISTORY_TURNS)
        ]

    llm = create_llm_service()
    try:
        answer = llm.generate(_SYSTEM_PROMPT, _build_user_prompt(history, message))
    except LLMError as exc:
        logger.error("General chat LLM error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if conversation is None:
        conversation = conversations.create(
            current_user.id, KIND_ASSISTANT, _title_from(message)
        )
    conversations.add_message(conversation, "user", message)
    conversations.add_message(conversation, "assistant", answer)

    ActivityRepository().log(
        current_user.id,
        "assistant_chat",
        resource_id=conversation.id,
        resource_title=conversation.title,
    )
    return GeneralChatResponse(
        answer=answer, conversation_id=conversation.id, title=conversation.title
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    current_user: User = Depends(get_current_user),
) -> list[ConversationSummary]:
    """The user's saved chats, most recently active first."""

    return [
        ConversationSummary.of(conversation)
        for conversation in ConversationRepository().list(current_user.id, KIND_ASSISTANT)
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str, current_user: User = Depends(get_current_user)
) -> ConversationDetail:
    """One saved chat with all of its messages."""

    conversations = ConversationRepository()
    conversation = conversations.get(conversation_id, current_user.id)
    if conversation is None or conversation.kind != KIND_ASSISTANT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return ConversationDetail(
        **ConversationSummary.of(conversation).model_dump(),
        messages=[MessageOut.of(message) for message in conversations.messages(conversation.id)],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str, current_user: User = Depends(get_current_user)
) -> None:
    """Delete a saved chat."""

    if not ConversationRepository().delete(conversation_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")


def _title_from(message: str) -> str:
    """A short title from the opening message."""

    title = " ".join(message.split())
    return title if len(title) <= _TITLE_CHARS else title[: _TITLE_CHARS - 1].rstrip() + "…"


def _build_user_prompt(history: list, message: str) -> str:
    """Format conversation history and the latest message into a user prompt."""

    if not history:
        return message

    lines: list[str] = ["[Conversation so far]"]
    for turn in history[-_HISTORY_TURNS:]:
        label = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{label}: {turn.content}")
    lines.append(f"\n[Current question]\n{message}")
    return "\n".join(lines)
