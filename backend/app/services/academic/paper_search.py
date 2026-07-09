"""Academic paper search via Semantic Scholar with arXiv as fallback.

Single responsibility: turn a topic query into a list of paper records,
trying Semantic Scholar first and falling back to arXiv when that provider
fails or returns nothing.
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_SS_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_SS_FIELDS = "title,authors,year,abstract,openAccessPdf"
_ARXIV_URL = "https://export.arxiv.org/api/query"

_ATOM_NS = "http://www.w3.org/2005/Atom"


class PaperSearchError(Exception):
    """Raised when paper search fails on all available providers."""


@dataclass(frozen=True)
class Paper:
    """Metadata for a single academic paper."""

    paper_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    pdf_url: str | None = None


class PaperSearchService:
    """Search academic papers using Semantic Scholar, with arXiv fallback."""

    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    def search(self, query: str, limit: int = 10) -> list[Paper]:
        """Return papers matching ``query``.

        Tries Semantic Scholar first. Falls back to arXiv when Semantic
        Scholar is unavailable or returns no results.

        Args:
            query: Free-text topic query (e.g. "transformer attention neural").
            limit: Maximum papers to return (capped at 20).

        Returns:
            A list of :class:`Paper` records, most relevant first.

        Raises:
            PaperSearchError: If both providers fail.
        """

        query = query.strip()
        if not query:
            raise PaperSearchError("A search query is required.")

        limit = min(max(limit, 1), 20)

        try:
            papers = self._search_semantic_scholar(query, limit)
            if papers:
                return papers
            logger.info("Semantic Scholar returned no results; falling back to arXiv.")
        except PaperSearchError as exc:
            logger.warning(
                "Semantic Scholar search failed: %s; falling back to arXiv.", exc
            )

        return self._search_arxiv(query, limit)

    # ------------------------------------------------------------------
    # Private: Semantic Scholar
    # ------------------------------------------------------------------

    def _search_semantic_scholar(self, query: str, limit: int) -> list[Paper]:
        try:
            response = httpx.get(
                _SS_URL,
                params={"query": query, "fields": _SS_FIELDS, "limit": limit},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise PaperSearchError(
                f"Semantic Scholar request failed: {exc}"
            ) from exc

        papers: list[Paper] = []
        for item in data.get("data") or []:
            authors = [
                str(a.get("name") or "")
                for a in (item.get("authors") or [])
                if a.get("name")
            ]
            oap = item.get("openAccessPdf") or {}
            pdf_url: str | None = (
                oap.get("url") if isinstance(oap, dict) else None
            )
            papers.append(
                Paper(
                    paper_id=str(item.get("paperId") or ""),
                    title=str(item.get("title") or "Untitled"),
                    authors=authors,
                    year=item.get("year"),
                    abstract=item.get("abstract") or None,
                    pdf_url=pdf_url or None,
                )
            )
        return papers

    # ------------------------------------------------------------------
    # Private: arXiv
    # ------------------------------------------------------------------

    def _search_arxiv(self, query: str, limit: int) -> list[Paper]:
        try:
            response = httpx.get(
                _ARXIV_URL,
                params={
                    "search_query": f"all:{query}",
                    "max_results": limit,
                    "sortBy": "relevance",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PaperSearchError(f"arXiv request failed: {exc}") from exc

        return _parse_arxiv(response.text)


def _parse_arxiv(xml_text: str) -> list[Paper]:
    """Parse arXiv Atom XML into :class:`Paper` objects."""

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise PaperSearchError(f"Failed to parse arXiv response: {exc}") from exc

    papers: list[Paper] = []
    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        arxiv_id_url = (
            (entry.findtext(f"{{{_ATOM_NS}}}id") or "").strip()
        )
        arxiv_id = arxiv_id_url.rsplit("/", 1)[-1]

        title = (
            (entry.findtext(f"{{{_ATOM_NS}}}title") or "Untitled")
            .replace("\n", " ")
            .strip()
        )
        abstract_raw = entry.findtext(f"{{{_ATOM_NS}}}summary") or ""
        abstract = abstract_raw.replace("\n", " ").strip() or None

        year: int | None = None
        published = entry.findtext(f"{{{_ATOM_NS}}}published") or ""
        if published:
            try:
                year = int(published[:4])
            except ValueError:
                pass

        authors = [
            name_el.text or ""
            for author in entry.findall(f"{{{_ATOM_NS}}}author")
            for name_el in author.findall(f"{{{_ATOM_NS}}}name")
            if name_el.text
        ]

        pdf_url: str | None = None
        for link in entry.findall(f"{{{_ATOM_NS}}}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")
                break

        papers.append(
            Paper(
                paper_id=f"arxiv:{arxiv_id}",
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                pdf_url=pdf_url,
            )
        )
    return papers
