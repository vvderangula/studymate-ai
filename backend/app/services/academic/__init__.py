"""Academic search module: paper discovery, summarization, and Q&A."""

from app.services.academic.paper_academic_service import (
    PaperAcademicService,
    PaperSummaryError,
)
from app.services.academic.paper_search import (
    Paper,
    PaperSearchError,
    PaperSearchService,
)

__all__ = [
    "Paper",
    "PaperAcademicService",
    "PaperSearchError",
    "PaperSearchService",
    "PaperSummaryError",
]
