"""Application service orchestrating the YouTube processing pipeline.

Pipeline: validate URL -> retrieve transcript -> clean and join cues ->
split into chunks (shared ``TextChunker``) -> embed (shared embedding
provider) -> store in ChromaDB (shared ``ChromaService``) with timestamp
citation metadata -> persist video metadata. It deliberately reuses the same
chunking, embedding, and vector-store services as the PDF pipeline; only the
transcript source and timestamp citations are YouTube-specific.
"""

import logging
import re
from datetime import datetime, timezone

from app.models.youtube import YoutubeMetadata
from app.repositories.youtube_repository import YoutubeMetadataRepository
from app.services.chunk_storage import ChunkStorageService
from app.services.embeddings.base import EmbeddingService
from app.services.vector_store.chroma_service import ChromaService
from app.services.youtube.transcript_service import (
    TranscriptSegment,
    VideoTranscript,
    YoutubeTranscriptService,
)

logger = logging.getLogger(__name__)

STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

_WHITESPACE = re.compile(r"\s+")
_PREFIX_LEN = 60


def _collapse(text: str) -> str:
    """Collapse all runs of whitespace into single spaces."""

    return _WHITESPACE.sub(" ", text).strip()


def _format_timestamp(seconds: int) -> str:
    """Format a second offset as ``M:SS`` or ``H:MM:SS``."""

    total = max(int(seconds), 0)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class YoutubeProcessingError(Exception):
    """Raised when a YouTube video's transcript cannot be processed."""


class YoutubeProcessingService:
    """Coordinates transcript retrieval, chunking, embedding, and storage.

    Reuses the shared chunking, embedding, and vector-store services so no
    processing logic is duplicated. Also exposes :meth:`ensure_indexed` so it
    can act as the RAG pipeline's indexer, keeping chat reuse intact.
    """

    def __init__(
        self,
        transcripts: YoutubeTranscriptService,
        chunker,
        chunk_storage: ChunkStorageService,
        embeddings: EmbeddingService,
        chroma: ChromaService,
        repository: YoutubeMetadataRepository,
    ) -> None:
        self._transcripts = transcripts
        self._chunker = chunker
        self._chunk_storage = chunk_storage
        self._embeddings = embeddings
        self._chroma = chroma
        self._repository = repository

    def process(self, url: str, user_id: str | None = None) -> YoutubeMetadata:
        """Run the full pipeline for a YouTube ``url`` and persist metadata.

        Returns:
            The stored :class:`YoutubeMetadata` with completed status.

        Raises:
            InvalidYoutubeUrlError: If the URL is not a valid YouTube link.
            TranscriptUnavailableError: If no transcript is available.
            YoutubeProcessingError: If no chunks can be produced.
        """

        transcript = self._transcripts.fetch(url)

        full_text, offsets = self._flatten(transcript.segments)
        chunks = self._chunker.chunk(full_text)
        if not chunks:
            self._mark_failed(url, transcript, user_id)
            raise YoutubeProcessingError(
                "The transcript did not contain any usable text."
            )

        starts = self._chunk_start_seconds(full_text, offsets, chunks)
        self._chunk_storage.save(transcript.video_id, chunks)
        self._index(transcript.video_id, chunks, starts)

        record = YoutubeMetadata(
            video_id=transcript.video_id,
            url=url,
            title=transcript.title,
            duration=transcript.duration,
            thumbnail=transcript.thumbnail,
            created_at=datetime.now(timezone.utc),
            user_id=user_id,
            processing_status=STATUS_COMPLETED,
            processed_at=datetime.now(timezone.utc),
            chunk_count=len(chunks),
        )
        self._repository.upsert(record)
        logger.info(
            "Processed YouTube video %s: %d chunks",
            transcript.video_id,
            len(chunks),
        )
        return record

    def ensure_indexed(self, video_id: str) -> int:
        """Return the number of vectors stored for a video.

        The video is embedded during :meth:`process`, so this simply reports
        the current vector count. It satisfies the RAG pipeline's indexer
        contract, allowing the shared chat service to be reused unchanged.
        """

        return self._chroma.count(video_id)

    def _index(
        self,
        video_id: str,
        chunks: list[str],
        starts: list[int],
    ) -> None:
        """Embed and store transcript chunks with timestamp citations."""

        vectors = self._embeddings.embed_documents(chunks)
        ids = [f"{video_id}-{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "video_id": video_id,
                "chunk_index": index,
                "chunk_id": ids[index],
                "page": starts[index],
                "source_reference": _format_timestamp(starts[index]),
            }
            for index in range(len(chunks))
        ]
        self._chroma.add_documents(
            video_id,
            ids=ids,
            embeddings=vectors,
            documents=chunks,
            metadatas=metadatas,
        )

    def _mark_failed(self, url: str, transcript: VideoTranscript, user_id: str | None = None) -> None:
        """Record a failed processing attempt for a video."""

        self._repository.upsert(
            YoutubeMetadata(
                video_id=transcript.video_id,
                url=url,
                title=transcript.title,
                duration=transcript.duration,
                thumbnail=transcript.thumbnail,
                created_at=datetime.now(timezone.utc),
                user_id=user_id,
                processing_status=STATUS_FAILED,
                processed_at=datetime.now(timezone.utc),
            )
        )

    @staticmethod
    def _flatten(
        segments: list[TranscriptSegment],
    ) -> tuple[str, list[tuple[int, float]]]:
        """Join cues into clean text, tracking each cue's start offset.

        Returns:
            A tuple of ``(full_text, offsets)`` where ``offsets`` maps the
            character position at which each cue begins to its start time.
        """

        parts: list[str] = []
        offsets: list[tuple[int, float]] = []
        running = 0
        for segment in segments:
            text = _collapse(segment.text)
            if not text:
                continue
            if parts:
                running += 1  # the single space that will join this cue
            offsets.append((running, segment.start))
            parts.append(text)
            running += len(text)
        return " ".join(parts), offsets

    @staticmethod
    def _chunk_start_seconds(
        full_text: str,
        offsets: list[tuple[int, float]],
        chunks: list[str],
    ) -> list[int]:
        """Map each chunk to the start time (in seconds) of its first cue.

        Best-effort: locates each chunk's leading text within the combined
        transcript and picks the timestamp of the cue covering that position.
        Falls back to the previous timestamp when a chunk cannot be located.
        """

        if not offsets:
            return [0] * len(chunks)

        starts: list[int] = []
        cursor = 0
        for chunk in chunks:
            prefix = chunk[:_PREFIX_LEN]
            position = full_text.find(prefix, cursor) if prefix else -1
            if position == -1:
                position = full_text.find(prefix) if prefix else -1
            if position == -1:
                position = cursor
            else:
                cursor = position
            starts.append(int(_seconds_at(offsets, position)))
        return starts


def _seconds_at(offsets: list[tuple[int, float]], position: int) -> float:
    """Return the start time of the cue covering ``position``."""

    seconds = offsets[0][1]
    for offset, start in offsets:
        if offset <= position:
            seconds = start
        else:
            break
    return seconds
