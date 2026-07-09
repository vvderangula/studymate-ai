"""Unit tests for the text chunker service."""

import pytest

from app.services.text_chunker import TextChunker


def test_chunk_empty_text_returns_no_chunks() -> None:
    """Empty or whitespace-only text should yield no chunks."""

    chunker = TextChunker(chunk_size=100, overlap=10)

    assert chunker.chunk("   ") == []


def test_chunk_short_text_returns_single_chunk() -> None:
    """Text shorter than the chunk size should produce one chunk."""

    chunker = TextChunker(chunk_size=100, overlap=10)

    chunks = chunker.chunk("hello world")

    assert chunks == ["hello world"]


def test_chunk_splits_with_overlap() -> None:
    """Long text should be split into overlapping chunks."""

    chunker = TextChunker(chunk_size=10, overlap=2)
    text = "abcdefghijklmnopqrstuvwxyz"

    chunks = chunker.chunk(text)

    # step = 10 - 2 = 8 -> starts at 0, 8, 16, 24
    assert chunks[0] == "abcdefghij"
    assert chunks[1] == "ijklmnopqr"
    assert len(chunks) == 4


def test_invalid_overlap_raises() -> None:
    """Overlap equal to or larger than chunk size is invalid."""

    with pytest.raises(ValueError):
        TextChunker(chunk_size=10, overlap=10)
