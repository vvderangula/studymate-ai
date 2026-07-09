"""Service for splitting text into overlapping chunks."""

from app.core.config import settings


class TextChunker:
    """Splits text into fixed-size, overlapping chunks.

    Single responsibility: given a body of text, produce a list of chunks
    suitable for embedding and retrieval. Overlap preserves context across
    chunk boundaries.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> None:
        self._chunk_size = chunk_size or settings.chunk_size
        self._overlap = overlap if overlap is not None else settings.chunk_overlap

        if self._chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if not 0 <= self._overlap < self._chunk_size:
            raise ValueError("overlap must be in the range [0, chunk_size).")

    def chunk(self, text: str) -> list[str]:
        """Split ``text`` into overlapping chunks.

        Args:
            text: The source text to split.

        Returns:
            A list of non-empty text chunks in document order.
        """

        normalized = text.strip()
        if not normalized:
            return []

        step = self._chunk_size - self._overlap
        chunks: list[str] = []
        for start in range(0, len(normalized), step):
            chunk = normalized[start : start + self._chunk_size].strip()
            if chunk:
                chunks.append(chunk)

        return chunks
