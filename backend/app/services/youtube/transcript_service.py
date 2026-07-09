"""Retrieves YouTube video transcripts and lightweight metadata.

Single responsibility: turn a YouTube URL into a validated video id, its
transcript segments (text plus start times), and basic display metadata
(title and thumbnail). Heavy or optional third-party imports are performed
lazily so the application can start without them and tests can inject fakes.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_VIDEO_ID = r"[A-Za-z0-9_-]{11}"
_URL_PATTERNS = (
    re.compile(rf"(?:youtube\.com/watch\?(?:.*&)?v=)(?P<id>{_VIDEO_ID})"),
    re.compile(rf"(?:youtu\.be/)(?P<id>{_VIDEO_ID})"),
    re.compile(rf"(?:youtube\.com/embed/)(?P<id>{_VIDEO_ID})"),
    re.compile(rf"(?:youtube\.com/shorts/)(?P<id>{_VIDEO_ID})"),
    re.compile(rf"(?:youtube\.com/live/)(?P<id>{_VIDEO_ID})"),
)
_OEMBED_URL = "https://www.youtube.com/oembed"


class InvalidYoutubeUrlError(Exception):
    """Raised when a URL is not a recognizable YouTube video link."""


class TranscriptUnavailableError(Exception):
    """Raised when a video has no retrievable transcript."""


@dataclass(frozen=True)
class TranscriptSegment:
    """A single transcript cue: some text spoken at a start time."""

    text: str
    start: float


@dataclass(frozen=True)
class VideoTranscript:
    """A video's transcript segments plus basic display metadata."""

    video_id: str
    title: str
    thumbnail: str
    duration: int | None
    segments: list[TranscriptSegment]


def extract_video_id(url: str) -> str:
    """Return the 11-character video id contained in a YouTube URL.

    Args:
        url: A YouTube watch, short, embed, or ``youtu.be`` URL.

    Returns:
        The extracted video id.

    Raises:
        InvalidYoutubeUrlError: If no valid video id can be found.
    """

    candidate = (url or "").strip()
    if not candidate:
        raise InvalidYoutubeUrlError("A YouTube URL is required.")

    for pattern in _URL_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return match.group("id")

    raise InvalidYoutubeUrlError("Enter a valid YouTube video URL.")


class YoutubeTranscriptService:
    """Fetches transcripts and metadata for YouTube videos."""

    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    def fetch(self, url: str) -> VideoTranscript:
        """Validate ``url`` and retrieve its transcript and metadata.

        Raises:
            InvalidYoutubeUrlError: If the URL is not a valid YouTube link.
            TranscriptUnavailableError: If no transcript can be retrieved.
        """

        video_id = extract_video_id(url)
        segments = self._fetch_segments(video_id)
        if not segments:
            raise TranscriptUnavailableError(
                "No transcript is available for this video."
            )

        title, thumbnail = self._fetch_display_metadata(url, video_id)
        duration = self._estimate_duration(segments)
        return VideoTranscript(
            video_id=video_id,
            title=title,
            thumbnail=thumbnail,
            duration=duration,
            segments=segments,
        )

    def _fetch_segments(self, video_id: str) -> list[TranscriptSegment]:
        """Retrieve raw transcript cues for a video."""

        try:
            from youtube_transcript_api import (
                FailedToCreateConsentCookie,
                IpBlocked,
                NoTranscriptFound,
                RequestBlocked,
                TranscriptsDisabled,
                VideoUnavailable,
                YouTubeTranscriptApi,
            )
        except ImportError as exc:  # pragma: no cover - dependency missing
            raise TranscriptUnavailableError(
                "Transcript support is not available."
            ) from exc

        try:
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)

            try:
                transcript = transcript_list.find_manually_created_transcript(
                    ["en", "en-US", "en-GB"]
                )
            except NoTranscriptFound:
                try:
                    transcript = transcript_list.find_generated_transcript(
                        ["en", "en-US", "en-GB"]
                    )
                except NoTranscriptFound:
                    transcript = next(iter(transcript_list), None)

            if transcript is None:
                raise TranscriptUnavailableError(
                    "No transcript was found for this video."
                )

            raw = transcript.fetch()
        except TranscriptsDisabled as exc:
            logger.warning("Transcripts disabled for %s: %s", video_id, exc)
            raise TranscriptUnavailableError(
                "Transcripts are disabled for this video."
            ) from exc
        except VideoUnavailable as exc:
            logger.warning("Video unavailable for %s: %s", video_id, exc)
            raise TranscriptUnavailableError(
                "This video is unavailable or restricted in your region."
            ) from exc
        except (RequestBlocked, IpBlocked, FailedToCreateConsentCookie) as exc:
            logger.warning("Transcript access blocked for %s: %s", video_id, exc)
            raise TranscriptUnavailableError(
                "Transcript retrieval is temporarily blocked. Please try again later."
            ) from exc
        except NoTranscriptFound as exc:
            logger.warning("No transcript found for %s: %s", video_id, exc)
            raise TranscriptUnavailableError(
                "No transcript was found for this video."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - library raises many subtypes
            logger.warning("Transcript retrieval failed for %s: %s", video_id, exc)
            raise TranscriptUnavailableError(
                "Failed to retrieve transcript for this video."
            ) from exc

        segments: list[TranscriptSegment] = []
        for cue in raw:
            text = _cue_text(cue)
            if text:
                segments.append(
                    TranscriptSegment(text=text, start=_cue_start(cue))
                )
        return segments

    def _fetch_display_metadata(self, url: str, video_id: str) -> tuple[str, str]:
        """Return ``(title, thumbnail_url)`` for a video via oEmbed.

        Falls back to a generic title and the standard thumbnail URL when the
        oEmbed lookup fails, so processing can still proceed.
        """

        fallback_thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        try:
            response = httpx.get(
                _OEMBED_URL,
                params={"url": url, "format": "json"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            title = str(data.get("title") or "YouTube video")
            thumbnail = str(data.get("thumbnail_url") or fallback_thumbnail)
            return title, thumbnail
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("oEmbed lookup failed for %s: %s", video_id, exc)
            return "YouTube video", fallback_thumbnail

    @staticmethod
    def _estimate_duration(segments: list[TranscriptSegment]) -> int | None:
        """Approximate the video length from the last transcript cue."""

        if not segments:
            return None
        return int(segments[-1].start)


def _cue_text(cue: Any) -> str:
    """Return cue text from either dict-like or object-like transcript items."""

    if isinstance(cue, dict):
        return str(cue.get("text", "")).strip()
    return str(getattr(cue, "text", "")).strip()


def _cue_start(cue: Any) -> float:
    """Return cue start offset from either dict-like or object-like items."""

    if isinstance(cue, dict):
        return float(cue.get("start", 0.0))
    return float(getattr(cue, "start", 0.0))
