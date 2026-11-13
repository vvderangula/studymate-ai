"""Repository for processed text chunks (one document per chunk).

Chunks are the cleaned, split text of a PDF or video transcript, kept so a
source can be re-embedded (for example after changing embedding model)
without re-reading the original.
"""

from __future__ import annotations

from pymongo import ASCENDING

from app.core.database import Collections
from app.repositories.base import MongoRepository, utcnow


class ChunkRepository(MongoRepository):
    """The only component that reads or writes ``chunks``."""

    collection_name = Collections.CHUNKS

    def save(self, source_id: str, chunks: list[str]) -> None:
        """Replace all stored chunks for ``source_id``."""

        self.collection.delete_many({"source_id": source_id})
        if chunks:
            now = utcnow()
            self.collection.insert_many(
                [
                    {"source_id": source_id, "index": index, "text": text, "created_at": now}
                    for index, text in enumerate(chunks)
                ]
            )

    def load(self, source_id: str) -> list[str] | None:
        """Stored chunks for ``source_id`` in order, or ``None`` if none."""

        docs = list(
            self.collection.find({"source_id": source_id}, {"text": 1}).sort("index", ASCENDING)
        )
        return [doc["text"] for doc in docs] if docs else None

    def delete(self, source_id: str) -> None:
        """Remove all chunks for ``source_id``."""

        self.collection.delete_many({"source_id": source_id})
