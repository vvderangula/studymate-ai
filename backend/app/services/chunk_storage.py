"""Service for persisting processed text chunks on the local filesystem.

Chunks are stored locally (not in a vector database) as JSON files keyed
by the PDF's identifier. This keeps processed output available for later
phases without introducing embedding or vector-store dependencies.
"""

import json
from pathlib import Path

from app.core.config import settings


class ChunkStorageService:
    """Reads and writes processed chunk lists to local JSON files.

    Single responsibility: persist and retrieve the ordered list of text
    chunks produced for a given PDF.
    """

    def __init__(self) -> None:
        self._chunks_dir = Path(settings.chunks_dir)
        self._chunks_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_id: str, chunks: list[str]) -> Path:
        """Persist ``chunks`` for ``file_id`` and return the file path."""

        destination = self._chunks_dir / f"{file_id}.json"
        destination.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
        return destination

    def load(self, file_id: str) -> list[str] | None:
        """Return stored chunks for ``file_id``, or ``None`` if absent."""

        source = self._chunks_dir / f"{file_id}.json"
        if not source.is_file():
            return None
        return json.loads(source.read_text(encoding="utf-8"))
