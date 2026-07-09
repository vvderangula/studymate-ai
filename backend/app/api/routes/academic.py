"""HTTP routes for the AI Academic Search module."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import User
from app.repositories.activity_repository import ActivityRepository
from app.schemas.academic import (
    PaperAskRequest,
    PaperAskResponse,
    PaperItem,
    PaperSearchRequest,
    PaperSearchResponse,
    PaperSummarizeRequest,
    PaperSummarizeResponse,
)
from app.services.academic import (
    PaperAcademicService,
    PaperSearchError,
    PaperSearchService,
    PaperSummaryError,
)
from app.services.llm import HuggingFaceLLMService, LLMError
from app.services.rag import PromptBuilder

router = APIRouter(prefix="/academic", tags=["academic"])
logger = logging.getLogger(__name__)

_search_service = PaperSearchService()
_prompt_builder = PromptBuilder()


def get_academic_service() -> PaperAcademicService:
    """Provide a :class:`PaperAcademicService` wired with the shared AI components."""

    return PaperAcademicService(_prompt_builder, HuggingFaceLLMService())


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

    ActivityRepository().log(
        current_user.id,
        "research_search",
        resource_title=query,
    )
    return PaperSearchResponse(
        query=query,
        papers=[
            PaperItem(
                paper_id=paper.paper_id,
                title=paper.title,
                authors=paper.authors,
                year=paper.year,
                abstract=paper.abstract,
                pdf_url=paper.pdf_url,
            )
            for paper in papers
        ],
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

    ActivityRepository().log(
        current_user.id,
        "research_asked",
        resource_id=request.paper_id,
        resource_title=request.title,
    )
    return PaperAskResponse(
        paper_id=request.paper_id,
        question=question,
        answer=answer,
    )
