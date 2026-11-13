"""Repositories for academic search history and saved papers."""

from __future__ import annotations

import uuid

from pymongo import DESCENDING

from app.core.database import Collections
from app.models.paper import PaperSearch, SavedPaper
from app.repositories.base import MongoRepository, as_utc, utcnow


class PaperSearchRepository(MongoRepository):
    """The only component that reads or writes ``paper_searches``."""

    collection_name = Collections.PAPER_SEARCHES

    def save(self, user_id: str, query: str, papers: list[dict]) -> PaperSearch:
        doc = {
            "_id": uuid.uuid4().hex,
            "user_id": user_id,
            "query": query,
            "papers": papers,
            "created_at": utcnow(),
        }
        self.collection.insert_one(doc)
        return _to_search(doc)

    def list(self, user_id: str, limit: int = 20) -> list[PaperSearch]:
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", DESCENDING).limit(limit)
        return [_to_search(doc) for doc in cursor]

    def get(self, search_id: str, user_id: str) -> PaperSearch | None:
        doc = self.collection.find_one({"_id": search_id, "user_id": user_id})
        return _to_search(doc) if doc else None

    def delete(self, search_id: str, user_id: str) -> bool:
        return bool(self.collection.delete_one({"_id": search_id, "user_id": user_id}).deleted_count)

    def count(self) -> int:
        return self.collection.count_documents({})


class SavedPaperRepository(MongoRepository):
    """The only component that reads or writes ``saved_papers``."""

    collection_name = Collections.SAVED_PAPERS

    def remember(self, user_id: str, paper: dict) -> None:
        """Record (or refresh) a paper the user worked with."""

        self.collection.update_one(
            {"user_id": user_id, "paper_id": paper["paper_id"]},
            {
                "$set": {
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors") or [],
                    "year": paper.get("year"),
                    "abstract": paper.get("abstract"),
                    "pdf_url": paper.get("pdf_url"),
                    "updated_at": utcnow(),
                }
            },
            upsert=True,
        )

    def set_summary(self, user_id: str, paper_id: str, summary: str) -> None:
        self.collection.update_one(
            {"user_id": user_id, "paper_id": paper_id},
            {"$set": {"summary": summary, "updated_at": utcnow()}},
        )

    def touch(self, user_id: str, paper_id: str) -> None:
        self.collection.update_one(
            {"user_id": user_id, "paper_id": paper_id}, {"$set": {"updated_at": utcnow()}}
        )

    def get(self, user_id: str, paper_id: str) -> SavedPaper | None:
        doc = self.collection.find_one({"user_id": user_id, "paper_id": paper_id})
        return _to_paper(doc) if doc else None

    def list(self, user_id: str, limit: int = 50) -> list[SavedPaper]:
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", DESCENDING).limit(limit)
        return [_to_paper(doc) for doc in cursor]

    def delete(self, user_id: str, paper_id: str) -> bool:
        return bool(
            self.collection.delete_one({"user_id": user_id, "paper_id": paper_id}).deleted_count
        )

    def count(self) -> int:
        return self.collection.count_documents({})


def _to_search(doc: dict) -> PaperSearch:
    return PaperSearch(
        id=doc["_id"],
        user_id=doc["user_id"],
        query=doc["query"],
        created_at=as_utc(doc["created_at"]),
        papers=doc.get("papers", []),
    )


def _to_paper(doc: dict) -> SavedPaper:
    return SavedPaper(
        user_id=doc["user_id"],
        paper_id=doc["paper_id"],
        title=doc.get("title", ""),
        updated_at=as_utc(doc["updated_at"]),
        authors=doc.get("authors") or [],
        year=doc.get("year"),
        abstract=doc.get("abstract"),
        pdf_url=doc.get("pdf_url"),
        summary=doc.get("summary"),
    )
