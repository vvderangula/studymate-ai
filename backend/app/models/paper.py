"""Domain models for academic search history and saved papers."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PaperSearch:
    """A search the user ran, with the results it returned."""

    id: str
    user_id: str
    query: str
    created_at: datetime
    papers: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class SavedPaper:
    """A paper the user opened, with its AI summary if one was generated."""

    user_id: str
    paper_id: str
    title: str
    updated_at: datetime
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    pdf_url: str | None = None
    summary: str | None = None
