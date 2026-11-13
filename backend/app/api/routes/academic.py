"""HTTP routes for the AI Academic Search module."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.conversation import KIND_PAPER
from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.paper_repository import PaperSearchRepository, SavedPaperRepository
from app.schemas.academic import (
    PaperDetailResponse,
    PaperAskRequest,
    PaperAskResponse,
    PaperItem,
    PaperSearchRequest,
    PaperSearchResponse,
    PaperSummarizeRequest,
    PaperSummarizeResponse,
    SavedPaperItem,
    SearchHistoryItem,
)
from app.schemas.history import MessageOut
from app.services.academic import (
    PaperAcademicService,
    PaperSearchError,
    PaperSearchService,
    PaperSummaryError,
)
from app.services.llm import LLMError, create_llm_service
from app.services.rag import PromptBuilder

router = APIRouter(prefix="/academic", tags=["academic"])
logger = logging.getLogger(__name__)

_search_service = PaperSearchService()
_prompt_builder = PromptBuilder()


def get_academic_service() -> PaperAcademicService:
    """Provide a :class:`PaperAcademicService` wired with the shared AI components."""

    return PaperAcademicService(_prompt_builder, create_llm_service())


@router.post("/search", response_model=PaperSearchResponse)
def search_papers(
    request: PaperSearchRequest,
    current_user: User = Depends(get_current_user),
) -> PaperSearchResponse:
    """Search academic papers by topic.

    Tries Semantic Scholar first; falls back to arXiv when unavailable.
    Responds with 400 for an empty query and 503 when both providers fail.
    """

    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must not be empty.",
        )

    try:
        papers = _search_service.search(query, request.limit)
    except PaperSearchError as exc:
        logger.error("Paper search failed for '%s': %s", query, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paper search is currently unavailable. Please try again later.",
        ) from exc

    items = [
        PaperItem(
            paper_id=paper.paper_id,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            abstract=paper.abstract,
            pdf_url=paper.pdf_url,
        )
        for paper in papers
    ]
    saved = PaperSearchRepository().save(
        current_user.id, query, [item.model_dump() for item in items]
    )
    ActivityRepository().log(
        current_user.id,
        "research_search",
        resource_id=saved.id,
        resource_title=query,
    )
    return PaperSearchResponse(
        query=query, papers=items, search_id=saved.id, created_at=saved.created_at
    )


@router.post("/papers/summarize", response_model=PaperSummarizeResponse)
def summarize_paper(
    request: PaperSummarizeRequest,
    service: PaperAcademicService = Depends(get_academic_service),
    current_user: User = Depends(get_current_user),
) -> PaperSummarizeResponse:
    """Generate an AI summary for a paper.

    Produces Short Summary, Key Contributions, Important Findings, and
    Conclusion sections from the paper's abstract. Responds with 400 when no
    abstract is provided and 502 if the LLM backend fails.
    """

    try:
        summary = service.summarize(
            title=request.title,
            authors=request.authors,
            year=request.year,
            abstract=request.abstract,
        )
    except (PaperSummaryError, LLMError) as exc:
        logger.error("Summarization failed for paper %s: %s", request.paper_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    papers = SavedPaperRepository()
    papers.remember(current_user.id, request.model_dump())
    papers.set_summary(current_user.id, request.paper_id, summary)
    return PaperSummarizeResponse(paper_id=request.paper_id, summary=summary)


@router.post("/papers/ask", response_model=PaperAskResponse)
def ask_paper(
    request: PaperAskRequest,
    service: PaperAcademicService = Depends(get_academic_service),
    current_user: User = Depends(get_current_user),
) -> PaperAskResponse:
    """Answer a question about a paper using its abstract as context."""

    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )

    try:
        answer = service.ask(
            title=request.title,
            abstract=request.abstract,
            question=question,
        )
    except LLMError as exc:
        logger.error("Paper Q&A failed for %s: %s", request.paper_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    papers = SavedPaperRepository()
    if papers.get(current_user.id, request.paper_id) is None:
        papers.remember(
            current_user.id,
            {"paper_id": request.paper_id, "title": request.title, "abstract": request.abstract},
        )
    else:
        papers.touch(current_user.id, request.paper_id)
    conversations = ConversationRepository()
    conversation = conversations.get_or_create_for_source(
        current_user.id, KIND_PAPER, request.paper_id, request.title
    )
    conversations.add_message(conversation, "user", question)
    conversations.add_message(conversation, "assistant", answer)

    ActivityRepository().log(
        current_user.id,
        "research_asked",
        resource_id=request.paper_id,
        resource_title=request.title,
    )
    return PaperAskResponse(
        conversation_id=conversation.id,
        paper_id=request.paper_id,
        question=question,
        answer=answer,
    )


def _paper_item(saved) -> PaperItem:
    return PaperItem(
        paper_id=saved.paper_id,
        title=saved.title,
        authors=saved.authors,
        year=saved.year,
        abstract=saved.abstract,
        pdf_url=saved.pdf_url,
    )


@router.get("/searches", response_model=list[SearchHistoryItem])
def list_searches(current_user: User = Depends(get_current_user)) -> list[SearchHistoryItem]:
    """The user's recent searches, newest first."""

    return [
        SearchHistoryItem(
            id=search.id,
            query=search.query,
            result_count=len(search.papers),
            created_at=search.created_at,
        )
        for search in PaperSearchRepository().list(current_user.id)
    ]


@router.get("/searches/{search_id}", response_model=PaperSearchResponse)
def get_search(
    search_id: str, current_user: User = Depends(get_current_user)
) -> PaperSearchResponse:
    """Reopen a past search with the results it returned (no new lookup)."""

    search = PaperSearchRepository().get(search_id, current_user.id)
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found.")
    return PaperSearchResponse(
        query=search.query,
        papers=[PaperItem(**paper) for paper in search.papers],
        search_id=search.id,
        created_at=search.created_at,
    )


@router.delete("/searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_search(search_id: str, current_user: User = Depends(get_current_user)) -> None:
    """Remove a search from history."""

    if not PaperSearchRepository().delete(search_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found.")


@router.get("/papers", response_model=list[SavedPaperItem])
def list_saved_papers(current_user: User = Depends(get_current_user)) -> list[SavedPaperItem]:
    """Papers the user summarised or asked about, most recent first."""

    conversations = {
        conversation.source_id: conversation
        for conversation in ConversationRepository().list(current_user.id, KIND_PAPER, limit=500)
    }
    items = []
    for saved in SavedPaperRepository().list(current_user.id):
        conversation = conversations.get(saved.paper_id)
        items.append(
            SavedPaperItem(
                paper=_paper_item(saved),
                has_summary=bool(saved.summary),
                message_count=conversation.message_count if conversation else 0,
                updated_at=saved.updated_at,
            )
        )
    return items


# ``:path`` because arXiv ids can contain "/" (e.g. arxiv:hep-th/9901001).
@router.get("/papers/{paper_id:path}", response_model=PaperDetailResponse)
def get_saved_paper(
    paper_id: str, current_user: User = Depends(get_current_user)
) -> PaperDetailResponse:
    """The saved summary and Q&A for one paper (404 if never saved)."""

    saved = SavedPaperRepository().get(current_user.id, paper_id)
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not saved.")
    conversations = ConversationRepository()
    conversation = conversations.find_for_source(current_user.id, KIND_PAPER, paper_id)
    return PaperDetailResponse(
        paper=_paper_item(saved),
        summary=saved.summary,
        conversation_id=conversation.id if conversation else None,
        messages=(
            [MessageOut.of(message) for message in conversations.messages(conversation.id)]
            if conversation
            else []
        ),
    )


@router.delete("/papers/{paper_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_paper(paper_id: str, current_user: User = Depends(get_current_user)) -> None:
    """Forget a paper: its summary and Q&A."""

    ConversationRepository().delete_for_source(current_user.id, KIND_PAPER, paper_id)
    if not SavedPaperRepository().delete(current_user.id, paper_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not saved.")
