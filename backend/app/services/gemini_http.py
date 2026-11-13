"""Shared HTTP call to the Gemini API with retry on rate limits and outages."""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

# 429 = rate limited (common on the free tier); 5xx = temporary outage.
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 5
_MAX_WAIT_SECONDS = 30.0


def post_with_retry(
    url: str, *, api_key: str, payload: dict, timeout: float
) -> httpx.Response:
    """POST to Gemini, retrying rate limits and server errors with backoff.

    Waits 2s, 4s, 8s, 16s between attempts, or the server's Retry-After when
    it sends one. Raises ``httpx.HTTPStatusError`` / ``httpx.HTTPError`` once
    retries are exhausted, so callers keep their existing error mapping.
    """

    headers = {"x-goog-api-key": api_key}
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            if attempt == _MAX_ATTEMPTS:
                raise
            wait = 2.0**attempt
            logger.warning("Gemini request failed (%s); retrying in %.0fs", exc, wait)
            time.sleep(wait)
            continue

        if response.status_code in _RETRY_STATUSES and attempt < _MAX_ATTEMPTS:
            wait = _retry_after(response) or 2.0**attempt
            wait = min(wait, _MAX_WAIT_SECONDS)
            logger.warning(
                "Gemini returned %s; retrying in %.0fs (attempt %d/%d)",
                response.status_code,
                wait,
                attempt,
                _MAX_ATTEMPTS,
            )
            time.sleep(wait)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError("unreachable")  # pragma: no cover


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    try:
        return float(value) if value else None
    except ValueError:
        return None
