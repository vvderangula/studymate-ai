"""Regression tests for YouTube metadata repository ownership behavior."""

from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.models.youtube import YoutubeMetadata
from app.repositories.youtube_repository import YoutubeMetadataRepository


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolate the database per test."""



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


def test_same_video_belongs_to_each_user_separately(env) -> None:
    """Two users processing one video each keep their own record."""

    repo = YoutubeMetadataRepository()
    video_id = "samevideo123"

    repo.upsert(_record(video_id, "user-a"))
    repo.upsert(_record(video_id, "user-b"))

    assert YoutubeMetadataRepository(user_id="user-a").get(video_id).user_id == "user-a"
    assert YoutubeMetadataRepository(user_id="user-b").get(video_id).user_id == "user-b"
    assert any(item.video_id == video_id for item in repo.list_by_user("user-a"))
    assert any(item.video_id == video_id for item in repo.list_by_user("user-b"))


def test_reprocessing_updates_the_same_record(env) -> None:
    """Processing a video again updates that user's record, not a duplicate."""

    repo = YoutubeMetadataRepository()
    repo.upsert(_record("vid1", "user-a"))
    repo.upsert(_record("vid1", "user-a"))

    assert len(repo.list_by_user("user-a")) == 1
