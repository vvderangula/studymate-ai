"""Tests for the AI Assistant general chat endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes.assistant import general_chat, _build_user_prompt
from app.main import app
from app.schemas.assistant import ChatTurn

client = TestClient(app)


# ------------------------------------------------------------------
# _build_user_prompt unit tests
# ------------------------------------------------------------------


def test_build_user_prompt_no_history() -> None:
    """With no history, the prompt should just be the message itself."""

    result = _build_user_prompt([], "What is photosynthesis?")
    assert result == "What is photosynthesis?"


def test_build_user_prompt_with_history() -> None:
    """History should be prepended to the latest message."""

    history = [
        ChatTurn(role="user", content="Hello"),
        ChatTurn(role="assistant", content="Hi there!"),
    ]
    result = _build_user_prompt(history, "Tell me more.")
    assert "Hello" in result
    assert "Hi there!" in result
    assert "Tell me more." in result


def test_build_user_prompt_caps_history_at_ten_turns() -> None:
    """History should be capped at the last 10 turns."""

    history = [
        ChatTurn(role="user", content=f"msg{i}") for i in range(20)
    ]
    result = _build_user_prompt(history, "latest")
    # Only last 10 should appear; first 10 should be absent
    assert "msg19" in result
    assert "msg0" not in result


# ------------------------------------------------------------------
# API route tests
# ------------------------------------------------------------------


class _StubLLM:
    """Replaces HuggingFaceLLMService in route tests."""

    def __init__(self, answer: str) -> None:
        self._answer = answer

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return self._answer


def test_chat_route_rejects_empty_message(auth_headers) -> None:
    """An empty message should be rejected with 400."""

    response = client.post("/assistant/chat", json={"message": "   "}, headers=auth_headers)
    assert response.status_code == 400


def test_chat_route_accepts_valid_message(monkeypatch, auth_headers) -> None:
    """A valid message should call the LLM and return 200."""

    import app.api.routes.assistant as route_module

    monkeypatch.setattr(
        route_module,
        "create_llm_service",
        lambda: _StubLLM("Photosynthesis is the process…"),
    )

    response = client.post(
        "/assistant/chat",
        json={"message": "What is photosynthesis?", "history": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "Photosynthesis" in response.json()["answer"]


def test_chat_route_passes_history_to_llm(monkeypatch, auth_headers) -> None:
    """History turns should be included in the user prompt sent to the LLM."""

    import app.api.routes.assistant as route_module

    captured: dict = {}

    class _CaptureLLM:
        def generate(self, system_prompt: str, user_prompt: str) -> str:
            captured["user_prompt"] = user_prompt
            return "answer"

    monkeypatch.setattr(route_module, "create_llm_service", lambda: _CaptureLLM())

    response = client.post(
        "/assistant/chat",
        json={
            "message": "Follow-up question",
            "history": [
                {"role": "user", "content": "Previous question"},
                {"role": "assistant", "content": "Previous answer"},
            ],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Previous question" in captured["user_prompt"]
    assert "Previous answer" in captured["user_prompt"]


def test_chat_route_no_history_field(auth_headers) -> None:
    """history is optional; omitting it should not error."""

    response = client.post("/assistant/chat", json={"message": "Hi"}, headers=auth_headers)
    # Will get 502 if no HF key is configured, not 422 or 400
    assert response.status_code in (200, 502)
