"""Pydantic schemas for the AI Academic Search feature."""

from pydantic import BaseModel, Field


class PaperSearchRequest(BaseModel):
    """A request to search academic papers by topic query."""

    query: str
    limit: int = Field(default=10, ge=1, le=20)


class PaperItem(BaseModel):
    """A single academic paper returned by search."""

    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    pdf_url: str | None = None


class PaperSearchResponse(BaseModel):
    """Search results for a topic query."""

    query: str
    papers: list[PaperItem]


class PaperSummarizeRequest(BaseModel):
    """A request to generate an AI summary for a paper."""

    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str | None = None


class PaperSummarizeResponse(BaseModel):
    """An AI-generated Markdown summary of a paper."""

    paper_id: str
    summary: str


class PaperAskRequest(BaseModel):
    """A request to ask a question about a paper."""

    paper_id: str
    title: str
    abstract: str | None = None
    question: str


class PaperAskResponse(BaseModel):
    """An AI-generated answer to a question about a paper."""

    paper_id: str
    question: str
    answer: str
