"""Shared pytest fixtures for integration tests.

Tests never touch the real MongoDB: an in-memory database (mongomock) is
installed before the app is imported, and replaced with a fresh one for
every test.
"""

import uuid

import mongomock
import pytest

from app.core.database import init_db, use_database

use_database(mongomock.MongoClient(tz_aware=True)["studymate_test"])

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

_client = TestClient(app)


@pytest.fixture
def auth_token() -> str:
    """Register a unique test user and return a valid Bearer token."""
    email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    response = _client.post(
        "/auth/register",
        json={"full_name": "Test User", "email": email, "password": "testpassword123"},
    )
    assert response.status_code == 201, f"Registration failed: {response.json()}"
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Return Authorization headers for a fresh test user."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(autouse=True)
def fresh_database():
    """Give every test its own empty in-memory database."""

    use_database(mongomock.MongoClient(tz_aware=True)["studymate_test"])
    init_db()
    yield
