"""Shared pytest fixtures for integration tests."""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

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
