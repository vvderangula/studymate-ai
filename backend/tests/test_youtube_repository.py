"""Regression tests for YouTube metadata repository ownership behavior."""

from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.core.database import init_db
from app.models.youtube import YoutubeMetadata
from app.repositories.youtube_repository import YoutubeMetadataRepository


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolate the database per test."""

    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    init_db()


def _record(video_id: str, user_id: str) -> YoutubeMetadata:
    now = datetime.now(timezone.utc)
    return YoutubeMetadata(
        video_id=video_id,
        url=f"https://youtu.be/{video_id}",
        title="Sample Video",
        duration=120,
        thumbnail="https://img.example/test.jpg",
        created_at=now,
        user_id=user_id,
        processing_status="completed",
        processed_at=now,
        chunk_count=3,
    )


def test_upsert_conflict_updates_video_owner(env) -> None:
    """Reprocessing an existing video id must update ownership to current user."""

    repo = YoutubeMetadataRepository()
    video_id = "samevideo123"

    repo.upsert(_record(video_id, "user-a"))
    repo.upsert(_record(video_id, "user-b"))

    stored = repo.get(video_id)
    assert stored is not None
    assert stored.user_id == "user-b"

    assert all(item.video_id != video_id for item in repo.list_by_user("user-a"))
    assert any(item.video_id == video_id for item in repo.list_by_user("user-b"))
