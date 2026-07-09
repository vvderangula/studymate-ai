"""HTTP routes for the AI Assistant – general chat endpoint.

Uses the shared HuggingFaceLLMService directly (no RAG). The frontend
maintains full conversation history; each request includes previous turns so
the model can produce contextually aware replies without server-side session
state.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.assistant import GeneralChatRequest, GeneralChatResponse
from app.services.llm import HuggingFaceLLMService, LLMError

router = APIRouter(prefix="/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are StudyMate AI, a helpful and knowledgeable study assistant. "
    "Answer the user's questions clearly, accurately, and concisely. "
    "You may discuss any educational topic."
)


@router.post("/chat", response_model=GeneralChatResponse)
def general_chat(request: GeneralChatRequest) -> GeneralChatResponse:
    """Generate a reply to a general question.

    The frontend sends the full conversation history in ``history`` so the
    model can maintain context across turns. Responds with 400 for an empty
    message and 502 if the LLM backend fails.
    """

    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must not be empty.",
        )

    # Build the user prompt: prepend recent history as context so the model
    # produces a contextually aware reply without any server-side state.
    user_prompt = _build_user_prompt(request.history, message)

    llm = HuggingFaceLLMService()
    try:
        answer = llm.generate(_SYSTEM_PROMPT, user_prompt)
    except LLMError as exc:
        logger.error("General chat LLM error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return GeneralChatResponse(answer=answer)


def _build_user_prompt(history: list, message: str) -> str:
    """Format conversation history and the latest message into a user prompt."""

    if not history:
        return message

    lines: list[str] = ["[Conversation so far]"]
    for turn in history[-10:]:  # cap at last 10 turns to stay within token limits
        label = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{label}: {turn.content}")
    lines.append(f"\n[Current question]\n{message}")
    return "\n".join(lines)
