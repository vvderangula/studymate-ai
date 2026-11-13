"""Stored history: assistant chats, study-tool outputs, and admin access."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.study_tools.quiz_service import QuizQuestion

client = TestClient(app)


class _EchoLLM:
    """Replies with the prompt it received, so context can be inspected."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return f"echo: {user_prompt}"


def _use_echo_llm(monkeypatch) -> None:
    import app.api.routes.assistant as assistant_routes

    monkeypatch.setattr(assistant_routes, "create_llm_service", lambda: _EchoLLM())


# ---------------------------------------------------------------- assistant
def test_assistant_chat_is_saved_and_listed(monkeypatch, auth_headers) -> None:
    _use_echo_llm(monkeypatch)

    first = client.post("/assistant/chat", json={"message": "What is entropy?"}, headers=auth_headers)
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]
    assert first.json()["title"] == "What is entropy?"

    listed = client.get("/assistant/conversations", headers=auth_headers).json()
    assert [item["id"] for item in listed] == [conversation_id]
    assert listed[0]["message_count"] == 2

    detail = client.get(f"/assistant/conversations/{conversation_id}", headers=auth_headers).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][0]["text"] == "What is entropy?"


def test_assistant_continues_with_stored_context(monkeypatch, auth_headers) -> None:
    _use_echo_llm(monkeypatch)

    first = client.post("/assistant/chat", json={"message": "Define osmosis"}, headers=auth_headers)
    conversation_id = first.json()["conversation_id"]

    second = client.post(
        "/assistant/chat",
        json={"message": "Give an example", "conversation_id": conversation_id},
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id
    # The stored first turn was sent back to the model as context.
    assert "Define osmosis" in second.json()["answer"]

    detail = client.get(f"/assistant/conversations/{conversation_id}", headers=auth_headers).json()
    assert detail["message_count"] == 4


def test_assistant_conversations_are_private(monkeypatch, auth_headers) -> None:
    _use_echo_llm(monkeypatch)
    conversation_id = client.post(
        "/assistant/chat", json={"message": "Mine"}, headers=auth_headers
    ).json()["conversation_id"]

    other = client.post(
        "/auth/register",
        json={"full_name": "Other", "email": "other@example.com", "password": "testpassword123"},
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other}"}

    assert client.get(f"/assistant/conversations/{conversation_id}", headers=other_headers).status_code == 404
    assert client.get("/assistant/conversations", headers=other_headers).json() == []


def test_assistant_conversation_delete(monkeypatch, auth_headers) -> None:
    _use_echo_llm(monkeypatch)
    conversation_id = client.post(
        "/assistant/chat", json={"message": "Temp"}, headers=auth_headers
    ).json()["conversation_id"]

    assert client.delete(f"/assistant/conversations/{conversation_id}", headers=auth_headers).status_code == 204
    assert client.get("/assistant/conversations", headers=auth_headers).json() == []


# --------------------------------------------------------------- study tools
class _StubQuizService:
    def generate(self, source_id: str, **kwargs):
        return [
            QuizQuestion(
                type="mcq",
                question="2 + 2?",
                options=["3", "4"],
                correct_answer="4",
                explanation="Arithmetic.",
            )
        ]


class _StubNotesService:
    def generate(self, source_id: str, **kwargs) -> str:
        return "# Notes\n\n- point"


def test_quiz_and_notes_are_saved_and_reopened(auth_headers) -> None:
    from app.api.routes.study_tools import get_notes_service, get_quiz_service

    app.dependency_overrides[get_quiz_service] = lambda: _StubQuizService()
    app.dependency_overrides[get_notes_service] = lambda: _StubNotesService()
    try:
        quiz = client.post(
            "/study-tools/quiz",
            json={"source_id": "s1", "source_type": "pdf", "question_type": "mcq",
                  "difficulty": "easy", "count": 5},
            headers=auth_headers,
        ).json()
        notes = client.post(
            "/study-tools/notes",
            json={"source_id": "s1", "source_type": "pdf", "note_type": "key_points"},
            headers=auth_headers,
        ).json()
    finally:
        app.dependency_overrides.clear()

    assert quiz["id"] and notes["id"]

    history = client.get("/study-tools/history", headers=auth_headers).json()["items"]
    assert {item["kind"] for item in history} == {"quiz", "notes"}

    reopened = client.get(f"/study-tools/quizzes/{quiz['id']}", headers=auth_headers).json()
    assert reopened["questions"][0]["correct_answer"] == "4"
    reopened_notes = client.get(f"/study-tools/notes/{notes['id']}", headers=auth_headers).json()
    assert reopened_notes["content"].startswith("# Notes")

    assert client.delete(f"/study-tools/quizzes/{quiz['id']}", headers=auth_headers).status_code == 204
    kinds = [item["kind"] for item in client.get("/study-tools/history", headers=auth_headers).json()["items"]]
    assert kinds == ["notes"]


# --------------------------------------------------------------------- admin
def test_admin_routes_reject_regular_users(monkeypatch, auth_headers) -> None:
    monkeypatch.setattr(settings, "admin_emails", ["someone-else@example.com"])

    assert client.get("/admin/stats", headers=auth_headers).status_code == 403
    assert client.get("/admin/users", headers=auth_headers).status_code == 403


def test_admin_sees_stats_and_users(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_emails", ["boss@example.com"])
    registered = client.post(
        "/auth/register",
        json={"full_name": "Boss", "email": "boss@example.com", "password": "testpassword123"},
    ).json()
    assert registered["role"] == "admin"
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    stats = client.get("/admin/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["totals"]["users"] == 1
    assert len(stats.json()["signups_daily"]) == 14

    users = client.get("/admin/users", headers=headers).json()
    assert users[0]["email"] == "boss@example.com"
    assert users[0]["role"] == "admin"
    assert "password_hash" not in users[0]
